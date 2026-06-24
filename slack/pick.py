#!/usr/bin/env python3
"""
pick.py: the rotation "schematic" that decides what Know-It-Owl should post next.

Pure, deterministic, no network, no file writes. It reads the fact library and
answers ONE question: post a FRESH never-seen fact, or RECIRCULATE an evergreen
`core` fact that is past its cooldown (which then must be reworded). This is the
decision engine behind the /owl-post command and the autonomous mid-week review.

(Named pick.py, not select.py, on purpose: a module called select.py shadows the
stdlib `select` that urllib/socket import, which breaks post.py's import.)

It does NOT send anything and does NOT touch fact files. Posting still goes only
through slack/post.py. Rewording a recirculated core fact is done by the caller
(a human, or Claude via /owl-post) in Know-It-Owl's voice; this script only picks
and explains why.

Policy (config/rotation.md):
  Pool = facts/approved/ (fresh, unseen)
         PLUS facts/posted/ where tier==core and weeks_since(posted_date) >= cooldown_weeks.
         (trivia never recirculates; it is sent once and retired.)
  Prefer fresh. Aim for ~1 core refresher every 3 to 4 weeks (--core-every,
  default 3): when at least that long has passed since the last core post to
  #codeleap-home and a core fact is due, recirculate instead. If one pool is
  empty, use the other. If both are empty, the decision is "none".

Usage:
  python3 slack/pick.py                # human-readable decision
  python3 slack/pick.py --json         # machine-readable (used by /owl-post)
  python3 slack/pick.py --core-every 4 # tune the refresher cadence
  python3 slack/pick.py --today 2026-06-16 --root /tmp/fixture   # for testing
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

# Reuse post.py's parsing so the two scripts can never disagree on the schema.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import post  # noqa: E402  (fm_get / get_post_history / body_hash / ROOT)


def split_fm(text):
    """Like post.split_frontmatter but never exits: returns (None, None) on miss."""
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def parse_date(s):
    # Tolerate quoted values: post.py writes dates unquoted, but the schema and
    # hand-edited files may show posted_date: "YYYY-MM-DD".
    s = (s or "").strip().strip('"').strip("'").strip()
    try:
        return date.fromisoformat(s)
    except Exception:
        return None


def weeks_between(then, today):
    return (today - then).days // 7


def nested_get(fm, parent, key):
    """Read a one-level-nested scalar (e.g. source.url). fm_get only sees top level."""
    in_parent = False
    for ln in fm.splitlines():
        if re.match(rf"^{re.escape(parent)}:\s*$", ln):
            in_parent = True
            continue
        if in_parent:
            if re.match(r"^\S", ln):  # dedented back to a top-level key
                break
            m = re.match(rf"^\s+{re.escape(key)}:\s*(.*)$", ln)
            if m:
                return m.group(1).strip().strip('"').strip("'")
    return ""


def mentions_people(fm):
    """True if people_mentioned is a non-empty inline or block list."""
    raw = (post.fm_get(fm, "people_mentioned", "[]") or "[]").strip()
    if raw and raw not in ("[]", "[ ]"):
        return True
    return bool(re.search(r"^people_mentioned:\s*$\n(?:\s+-\s+.*\n?)+", fm, re.M))


def load_fact(path, kind):
    fm, body = split_fm(path.read_text())
    if fm is None:
        return None
    cd_raw = post.fm_get(fm, "cooldown_weeks", "0") or "0"
    cd = int(re.sub(r"\D", "", cd_raw) or "0")
    return {
        "path": path,
        "fm": fm,
        "kind": kind,  # "fresh" or "recirculate"
        "body": (body or "").strip(),
        "id": post.fm_get(fm, "id", path.stem),
        "status": post.fm_get(fm, "status", "candidate"),
        "tier": post.fm_get(fm, "tier", "trivia"),
        "category": post.fm_get(fm, "category", "") or "",
        "cooldown_weeks": cd,
        "posted_date": post.fm_get(fm, "posted_date", "") or "",
        "mentions_people": mentions_people(fm),
        "source_type": nested_get(fm, "source", "type"),
        "source_url": nested_get(fm, "source", "url"),
        "history_len": len(post.get_post_history(fm)),
    }


def scan(d, kind):
    if not d.exists():
        return []
    facts = []
    for p in sorted(p for p in d.glob("*.md") if p.name != "README.md"):
        f = load_fact(p, kind)
        if f:
            facts.append(f)
    return facts


def last_core_home_date(posted_facts):
    """Most recent date a core fact was posted to #codeleap-home, across the library."""
    latest = None
    for f in posted_facts:
        if f["tier"] != "core":
            continue
        for e in post.get_post_history(f["fm"]):
            if e.get("channel") == "home":
                d = parse_date(e.get("date", ""))
                if d and (latest is None or d > latest):
                    latest = d
    return latest


def decide(root, today, core_every):
    fresh = scan(root / "facts" / "approved", "fresh")
    posted = scan(root / "facts" / "posted", "recirculate")

    # Eligible recirculation pool: core, in posted/, past cooldown.
    recirc = []
    skipped = []
    for f in posted:
        if f["tier"] != "core":
            continue
        pd = parse_date(f["posted_date"])
        if not pd:
            skipped.append(f["id"])  # core in posted/ with no usable posted_date
            continue
        w = weeks_between(pd, today)
        if w >= f["cooldown_weeks"]:
            f["weeks_since_posted"] = w
            f["overdue_weeks"] = w - f["cooldown_weeks"]
            recirc.append(f)
    # Most overdue first; tie-break by oldest posted_date, then filename.
    recirc.sort(key=lambda f: (-f["overdue_weeks"], f["posted_date"], f["path"].name))

    last_core = last_core_home_date(posted)
    weeks_since_core = weeks_between(last_core, today) if last_core else None
    due_for_core = (last_core is None) or (weeks_since_core >= core_every)

    recirculate_now = bool(recirc) and (due_for_core or not fresh)
    if recirculate_now:
        order = recirc + fresh
    elif fresh:
        order = fresh + recirc
    else:
        order = []

    pick = order[0] if order else None
    decision = pick["kind"] if pick else "none"

    if decision == "recirculate":
        if last_core:
            reason = (f"{weeks_since_core} week(s) since the last core refresher "
                      f"(target ~{core_every}), so it is time to recirculate. "
                      f"'{pick['id']}' is {pick['overdue_weeks']} week(s) past its "
                      f"{pick['cooldown_weeks']}-week cooldown. Rework the wording.")
        else:
            reason = (f"No core refresher on record yet and '{pick['id']}' is past "
                      f"its {pick['cooldown_weeks']}-week cooldown. Rework the wording.")
        if not fresh:
            reason += " (No fresh facts available.)"
    elif decision == "fresh":
        bits = [f"{len(fresh)} fresh fact(s) available; posting the oldest."]
        if last_core is not None:
            bits.append(f"Only {weeks_since_core} week(s) since the last core "
                        f"refresher (target ~{core_every}), so stay fresh.")
        if recirc:
            bits.append(f"{len(recirc)} core fact(s) are also due to recirculate.")
        reason = " ".join(bits)
    else:
        reason = ("Nothing to post: facts/approved/ is empty and no core fact in "
                  "facts/posted/ is past its cooldown.")

    return {
        "decision": decision,
        "reason": reason,
        "today": today.isoformat(),
        "core_every_weeks": core_every,
        "cadence": {
            "last_core_home_date": last_core.isoformat() if last_core else None,
            "weeks_since_last_core": weeks_since_core,
            "due_for_core": due_for_core,
        },
        "pools": {"fresh": len(fresh), "recirculate": len(recirc)},
        "skipped_core_no_date": skipped,
        "pick": fact_json(pick, root) if pick else None,
        # Ordered walk for a 'discard -> next' review loop: chosen pick first.
        "walk": [fact_json(f, root) for f in order],
    }


def fact_json(f, root):
    try:
        rel = str(f["path"].relative_to(root))
    except ValueError:
        rel = str(f["path"])
    return {
        "file": rel,
        "id": f["id"],
        "type": f["kind"],
        "tier": f["tier"],
        "category": f["category"],
        "status": f["status"],
        "needs_reword": f["kind"] == "recirculate",
        "mentions_people": f["mentions_people"],
        "source_type": f["source_type"],
        "source_url": f["source_url"],
        "cooldown_weeks": f["cooldown_weeks"],
        "weeks_since_posted": f.get("weeks_since_posted"),
        "overdue_weeks": f.get("overdue_weeks"),
        "prior_wording_count": f["history_len"],
        "current_body": f["body"],
    }


def print_human(d):
    print(f"decision: {d['decision'].upper()}   (today {d['today']})")
    print(f"  pools: fresh={d['pools']['fresh']}  recirculate-eligible={d['pools']['recirculate']}")
    c = d["cadence"]
    print(f"  cadence: last core refresher {c['last_core_home_date'] or 'never'}; "
          f"{c['weeks_since_last_core'] if c['weeks_since_last_core'] is not None else '-'} "
          f"week(s) ago; due_for_core={c['due_for_core']}")
    print(f"  why: {d['reason']}")
    if d["skipped_core_no_date"]:
        print(f"  note: skipped core facts in posted/ with no posted_date: "
              f"{', '.join(d['skipped_core_no_date'])}")
    p = d["pick"]
    if not p:
        print("  pick: (nothing to post)")
        return
    print(f"\n  PICK: {p['file']}")
    print(f"        id={p['id']}  tier={p['tier']}  type={p['type']}  "
          f"needs_reword={p['needs_reword']}")
    if p["type"] == "recirculate":
        print(f"        {p['overdue_weeks']} week(s) past a {p['cooldown_weeks']}-week "
              f"cooldown; {p['prior_wording_count']} prior wording(s) on record.")
    if p["mentions_people"]:
        print("        names a person -> roster-check before posting.")
    if len(d["walk"]) > 1:
        nxt = ", ".join(w["id"] for w in d["walk"][1:6])
        print(f"\n  next-if-discarded: {nxt}")


def main():
    ap = argparse.ArgumentParser(
        description="Decide whether Know-It-Owl posts a fresh fact or recirculates a core one.")
    ap.add_argument("--json", action="store_true", help="machine-readable output (used by /owl-post)")
    ap.add_argument("--core-every", type=int, default=3,
                    help="target weeks between core refreshers (default 3)")
    ap.add_argument("--today", help="override today's date (YYYY-MM-DD) for testing")
    ap.add_argument("--root", help="override the repo root (for testing fixtures)")
    args = ap.parse_args()

    root = Path(args.root).resolve() if args.root else post.ROOT
    today = parse_date(args.today) if args.today else date.today()
    if today is None:
        sys.exit(f"Bad --today value: {args.today!r} (want YYYY-MM-DD).")

    result = decide(root, today, args.core_every)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_human(result)


if __name__ == "__main__":
    main()
