#!/usr/bin/env python3
"""
post.py — the ONE entry point for sending a Know-It-Owl "Did you know?" fact.

It does two things so they can never drift apart:
  1. Sends the fact's body VERBATIM to Slack as Know-It-Owl.
  2. For a real post, updates the fact pipeline: stamps `posted_date`, appends to
     `post_history`, sets `status: posted`, and moves the file into facts/posted/.

A fact file = YAML frontmatter + a body. The body IS the exact Slack message.

Review vs real (this is the important part):
  --to test  (default)  preview in the test channel. Does NOT touch fact files.
  --to home             the real weekly post to #codeleap-home. Records + moves.
  --record              force the record+move even when --to test.
  --dry-run             show what would happen; send nothing, change nothing.

Examples:
  python3 slack/post.py --select --to home                       # weekly post
  python3 slack/post.py facts/approved/2026-foo.md --to home
  python3 slack/post.py facts/candidates/2026-foo.md             # test preview
  python3 slack/post.py facts/approved/2026-foo.md --to home --dry-run

Identity/avatar is controlled by .env (see SLACK_ICON_URL / SLACK_ICON_EMOJI) or
disabled entirely with --no-customize (posts as the raw app profile).
"""
import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env():
    env = {}
    envf = ROOT / ".env"
    if envf.exists():
        for line in envf.read_text().splitlines():
            m = re.match(r"\s*([A-Z_]+)\s*=\s*(.+?)\s*$", line)
            if m:
                env[m.group(1)] = m.group(2).strip()
    return env


def slack(method, token, payload):
    req = urllib.request.Request(
        f"https://slack.com/api/{method}",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json; charset=utf-8"},
    )
    return json.load(urllib.request.urlopen(req))


def split_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        sys.exit("Fact file has no '---' YAML frontmatter block.")
    return m.group(1), m.group(2)


def fm_get(fm, key, default=None):
    m = re.search(rf"^{re.escape(key)}:\s*(.*)$", fm, re.M)
    return m.group(1).strip() if m else default


def fm_set_scalar(fm, key, value):
    """Replace a top-level scalar key (or append it). Value injected safely."""
    pat = rf"^({re.escape(key)}:).*$"
    if re.search(pat, fm, re.M):
        return re.sub(pat, lambda m: f"{m.group(1)} {value}", fm, count=1, flags=re.M)
    return fm.rstrip("\n") + f"\n{key}: {value}"


def get_post_history(fm):
    raw = fm_get(fm, "post_history", "[]")
    try:
        return json.loads(raw)
    except Exception:
        return []


def body_hash(body):
    return hashlib.sha1(body.strip().encode("utf-8")).hexdigest()[:10]


def resolve_fact(args):
    if args.select:
        approved = sorted(
            p for p in (ROOT / "facts" / "approved").glob("*.md") if p.name != "README.md"
        )
        if not approved:
            sys.exit("Nothing in facts/approved/ to --select.")
        return approved[0]
    if not args.fact_file:
        sys.exit("Provide a fact file path, or use --select.")
    for cand in (ROOT / args.fact_file, Path(args.fact_file)):
        if cand.exists():
            return cand
    sys.exit(f"Fact file not found: {args.fact_file}")


def main():
    ap = argparse.ArgumentParser(description="Send a Know-It-Owl fact and update the pipeline.")
    ap.add_argument("fact_file", nargs="?", help="path to the fact .md (the body is posted verbatim)")
    ap.add_argument("--to", choices=["test", "home"], default="test",
                    help="test = preview (default), home = the real post to #codeleap-home")
    ap.add_argument("--select", action="store_true", help="ignore fact_file; pick oldest in facts/approved/")
    ap.add_argument("--record", action="store_true", help="record + move to posted/ even for --to test")
    ap.add_argument("--dry-run", action="store_true", help="show, but send nothing and change nothing")
    ap.add_argument("--no-customize", action="store_true", help="post as the raw app identity")
    args = ap.parse_args()

    env = load_env()
    token = env.get("SLACK_BOT_TOKEN")
    if not token:
        sys.exit("No SLACK_BOT_TOKEN in .env")

    if args.to == "home":
        channel = env.get("SLACK_HOME_CHANNEL_ID") or env.get("SLACK_HOME_CHANNEL")
    else:
        channel = env.get("SLACK_TEST_CHANNEL_ID")
    if not channel:
        sys.exit(f"No channel configured for --to {args.to} (check .env).")

    fact_path = resolve_fact(args)
    fm, body = split_frontmatter(fact_path.read_text())
    body = body.strip()
    if not body:
        sys.exit("Fact body is empty. The body IS the verbatim Slack message.")

    status = fm_get(fm, "status", "candidate")
    tier = fm_get(fm, "tier", "trivia")
    fact_id = fm_get(fm, "id", fact_path.stem)
    hist = get_post_history(fm)
    will_record = (args.to == "home" or args.record) and not args.dry_run

    # Guard: only approved (or already-posted core, for re-rotation) reach #codeleap-home.
    if args.to == "home" and status not in ("approved", "posted"):
        sys.exit(f"Refusing: '{fact_id}' has status '{status}'. Only approved facts go to "
                 f"#codeleap-home (promote it to facts/approved/ first).")

    # Guard: never repost identical wording (rotation rule). Reword to rotate a core fact.
    h = body_hash(body)
    if (args.to == "home" or args.record) and any(e.get("hash") == h for e in hist):
        when = next(e.get("date") for e in hist if e.get("hash") == h)
        sys.exit(f"Refusing: this exact wording was already posted on {when}. "
                 f"Reword before reposting (rotation rule).")

    payload = {"channel": channel, "text": body, "unfurl_links": False, "unfurl_media": False}
    if not args.no_customize:
        payload["username"] = "Know-It-Owl"
        if env.get("SLACK_ICON_URL"):
            payload["icon_url"] = env["SLACK_ICON_URL"]
        else:
            payload["icon_emoji"] = env.get("SLACK_ICON_EMOJI", ":owl:")

    print(f"fact={fact_id}  tier={tier}  status={status}  ->  {args.to} ({channel})")

    if args.dry_run:
        print("\n--- DRY RUN: would post this body ---\n" + body)
        print("\n--- and would " +
              ("RECORD (stamp posted_date, append post_history, status=posted, move to facts/posted/)"
               if (args.to == "home" or args.record)
               else "leave fact files UNCHANGED (review preview)") + " ---")
        return

    resp = slack("chat.postMessage", token, payload)
    if not resp.get("ok"):
        sys.exit(f"Slack error: {resp.get('error')}")
    ts = resp.get("ts")
    print(f"posted ok  ts={ts}")

    if not will_record:
        print("review preview: fact files left unchanged.")
        return

    today = date.today().isoformat()
    hist.append({"date": today, "channel": args.to, "ts": ts, "hash": h})
    fm = fm_set_scalar(fm, "status", "posted")
    fm = fm_set_scalar(fm, "posted_date", today)
    fm = fm_set_scalar(fm, "post_history", json.dumps(hist, ensure_ascii=False))
    new_text = f"---\n{fm}\n---\n\n{body}\n"

    dest = ROOT / "facts" / "posted" / fact_path.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(new_text)
    if fact_path.resolve() != dest.resolve():
        fact_path.unlink()
        print(f"recorded: {fact_path.relative_to(ROOT)}  ->  {dest.relative_to(ROOT)}")
    else:
        print(f"recorded in place: {dest.relative_to(ROOT)}")
    print(f"posted_date={today}; post_history entries={len(hist)}; status=posted; tier={tier}"
          + ("  (core: eligible to rotate again after cooldown_weeks)" if tier == "core" else "  (trivia: retired)"))


if __name__ == "__main__":
    main()
