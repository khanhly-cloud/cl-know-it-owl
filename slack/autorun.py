#!/usr/bin/env python3
"""
autorun.py: the mechanical cron entrypoint for the Know-It-Owl review loop.

No Claude needed. Reuses pick.py + post.py + review.py.
  announce  pick a fact; if FRESH, post it to the review channel and seed ✅/🗑️.
  resolve   poll the in-flight review; ✅ publishes via post.py --to home, 🗑️
            surfaces the next candidate.

A RECIRCULATED core fact needs a reworded body, which this script cannot generate,
so on a recirculate week announce posts a heads-up and exits (run /owl-post by hand
that week). State for the in-flight review lives in slack/.review-state.json.

Usage: python3 slack/autorun.py announce|resolve
"""
import sys, json, re, subprocess, urllib.request, urllib.parse
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import post, pick  # reuse the tested pieces

ROOT = post.ROOT
STATE = ROOT / "slack" / ".review-state.json"
APPROVE, DISCARD = "white_check_mark", "wastebasket"

env = post.load_env()
TOK = env.get("SLACK_BOT_TOKEN")
REVIEW = env.get("SLACK_REVIEW_CHANNEL_ID") or env.get("SLACK_TEST_CHANNEL_ID")


def ident():
    return ({"icon_url": env["SLACK_ICON_URL"]} if env.get("SLACK_ICON_URL")
            else {"icon_emoji": env.get("SLACK_ICON_EMOJI", ":owl:")})


def say(channel, text, thread_ts=None):
    p = {"channel": channel, "text": text, "unfurl_links": False,
         "unfurl_media": False, "username": "Know-It-Owl", **ident()}
    if thread_ts:
        p["thread_ts"] = thread_ts
    return post.slack("chat.postMessage", TOK, p)


def sget(method, params):
    url = "https://slack.com/api/%s?%s" % (method, urllib.parse.urlencode(params))
    return json.load(urllib.request.urlopen(
        urllib.request.Request(url, headers={"Authorization": "Bearer " + TOK})))


def is_member(uid):
    info = sget("users.info", {"user": uid})
    usr = info.get("user", {})
    return bool(info.get("ok") and not usr.get("deleted") and not usr.get("is_bot"))


def run_post(fact_file, to):
    """Send through the one script. Returns (ts_or_None, combined_output, returncode)."""
    r = subprocess.run([sys.executable, str(ROOT / "slack" / "post.py"), fact_file, "--to", to],
                       capture_output=True, text=True, cwd=str(ROOT))
    out = r.stdout + r.stderr
    m = re.search(r"ts=([0-9.]+)", out)
    return (m.group(1) if m else None), out, r.returncode


def announce(discarded=None):
    discarded = discarded or []
    d = pick.decide(ROOT, date.today(), 3)
    walk = [w for w in d["walk"] if w["id"] not in discarded]
    if not walk:
        print("announce: nothing to post (decision=%s)" % d["decision"])
        return 1
    item = walk[0]
    if item["needs_reword"]:
        say(REVIEW, "🦉 This week's pick is a *core refresher* (`%s`) that needs fresh "
                    "wording. Run `/owl-post` to reword and announce it. (autorun cannot "
                    "reword on its own.)" % item["id"])
        print("announce: recirculate pick %s needs a manual reword; notified." % item["id"])
        return 2
    ts, out, rc = run_post(item["file"], "test")
    if not ts:
        print("announce: post failed rc=%s\n%s" % (rc, out.strip()))
        return 1
    subprocess.run([sys.executable, str(ROOT / "slack" / "review.py"), "seed", ts,
                    "--channel", REVIEW], cwd=str(ROOT))
    STATE.write_text(json.dumps({"ts": ts, "channel": REVIEW, "fact_file": item["file"],
                                 "type": item["type"], "discarded": discarded}))
    say(REVIEW, "React ✅ to publish to the output channel, or 🗑️ to see another.", thread_ts=ts)
    print("announce: posted %s ts=%s" % (item["id"], ts))
    return 0


def resolve():
    if not STATE.exists():
        print("resolve: no review in flight")
        return 0
    s = json.loads(STATE.read_text())
    r = subprocess.run([sys.executable, str(ROOT / "slack" / "review.py"), "poll", s["ts"],
                        "--channel", s["channel"], "--json"], capture_output=True, text=True, cwd=str(ROOT))
    try:
        v = json.loads(r.stdout)
    except Exception:
        print("resolve: poll failed: %s" % (r.stdout + r.stderr).strip())
        return 1
    verdict = v.get("verdict")

    if verdict == "pending":
        print("resolve: pending (no human reaction yet)")
        return 0
    if verdict == "conflict":
        say(s["channel"], "🤔 Both ✅ and 🗑️ from a human. Please pick one.", thread_ts=s["ts"])
        print("resolve: conflict")
        return 0
    if verdict == "error":
        print("resolve: Slack error %s (see slack/AUTONOMOUS.md)" % v.get("error"))
        return 1
    if verdict == "approve":
        real = [u for u in v.get("approvers", []) if is_member(u)]
        if not real:
            print("resolve: approve reaction but no verified member; waiting")
            return 0
        ts, out, rc = run_post(s["fact_file"], "home")
        if rc != 0:
            print("resolve: home post failed:\n%s" % out.strip())
            return 1
        say(s["channel"], "✅ Approved and published. Recorded and moved to facts/posted/.",
            thread_ts=s["ts"])
        STATE.unlink(missing_ok=True)
        print("resolve: published %s" % s["fact_file"])
        return 0
    if verdict == "discard":
        say(s["channel"], "🗑️ Discarded. Surfacing the next candidate.", thread_ts=s["ts"])
        discarded = s.get("discarded", []) + [Path(s["fact_file"]).stem]
        STATE.unlink(missing_ok=True)
        return announce(discarded)
    print("resolve: unknown verdict %r" % verdict)
    return 1


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("announce", "resolve"):
        sys.exit("usage: autorun.py announce|resolve")
    if not TOK:
        sys.exit("autorun: no SLACK_BOT_TOKEN in .env")
    if not REVIEW:
        sys.exit("autorun: no review channel (set SLACK_REVIEW_CHANNEL_ID or SLACK_TEST_CHANNEL_ID)")
    sys.exit(announce() if sys.argv[1] == "announce" else resolve())


if __name__ == "__main__":
    main()
