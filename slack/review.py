#!/usr/bin/env python3
"""
review.py: reaction primitives for the autonomous mid-week review (Part B).

This is the no-server substitute for "Approve / Discard buttons". The review
message is posted to a channel the bot can read (via slack/post.py --to test),
then:

  seed   add the approve + discard emoji to that message (so a reviewer just clicks)
  poll   read the message's reactions and report a verdict (approve / discard /
         conflict / pending), so a scheduled job can act on it.

It does NOT post facts and does NOT touch fact files. The actual home post still
goes only through slack/post.py. The orchestration (post review -> seed -> wait ->
poll -> on approve promote+post, on discard show next) lives in slack/AUTONOMOUS.md.

Scopes (see AUTONOMOUS.md): poll needs `reactions:read`; seed needs
`reactions:write`. Neither is in the current grant, so this is staged until they
are added. A private review channel also needs `groups:history` + bot membership;
a PUBLIC review channel works with the already-granted `channels:history`.

Usage:
  python3 slack/review.py seed <ts> [--channel C...]
  python3 slack/review.py poll <ts> [--channel C...] [--json]
"""
import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import post  # noqa: E402  (load_env / slack)

APPROVE_EMOJI = "white_check_mark"   # ✅
DISCARD_EMOJI = "wastebasket"        # 🗑️


def slack_get(method, token, params):
    """Slack read methods (e.g. reactions.get) want a GET with query params."""
    url = f"https://slack.com/api/{method}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    return json.load(urllib.request.urlopen(req))


def resolve(args):
    env = post.load_env()
    token = env.get("SLACK_BOT_TOKEN")
    if not token:
        sys.exit("No SLACK_BOT_TOKEN in .env")
    channel = (args.channel
               or env.get("SLACK_REVIEW_CHANNEL_ID")
               or env.get("SLACK_TEST_CHANNEL_ID"))
    if not channel:
        sys.exit("No review channel (set --channel, SLACK_REVIEW_CHANNEL_ID, or "
                 "SLACK_TEST_CHANNEL_ID in .env).")
    return token, channel


def cmd_seed(args):
    token, channel = resolve(args)
    out = {}
    for name in (args.approve, args.discard):
        resp = post.slack("reactions.add", token,
                          {"channel": channel, "timestamp": args.ts, "name": name})
        out[name] = resp.get("ok", False)
        if not resp.get("ok") and resp.get("error") != "already_reacted":
            sys.exit(f"reactions.add {name} failed: {resp.get('error')} "
                     f"(need reactions:write and bot membership in {channel}).")
    print(json.dumps({"seeded": out, "channel": channel, "ts": args.ts}, ensure_ascii=False))


def cmd_poll(args):
    token, channel = resolve(args)

    # Who is the bot? So seeded reactions do not count as a human decision.
    me = post.slack("auth.test", token, {})
    bot_user = me.get("user_id") if me.get("ok") else None

    resp = slack_get("reactions.get", token,
                     {"channel": channel, "timestamp": args.ts, "full": "true"})
    if not resp.get("ok"):
        out = {"verdict": "error", "error": resp.get("error"), "channel": channel, "ts": args.ts}
        print(json.dumps(out, ensure_ascii=False))
        sys.exit(f"reactions.get failed: {resp.get('error')} "
                 f"(need reactions:read; for a private channel also groups:history).")

    reactions = (resp.get("message") or {}).get("reactions", [])
    by_name = {r["name"]: [u for u in r.get("users", []) if u != bot_user] for r in reactions}
    approvers = by_name.get(args.approve, [])
    discarders = by_name.get(args.discard, [])

    if approvers and discarders:
        verdict = "conflict"
    elif approvers:
        verdict = "approve"
    elif discarders:
        verdict = "discard"
    else:
        verdict = "pending"

    out = {
        "verdict": verdict,
        "channel": channel,
        "ts": args.ts,
        "approve_emoji": args.approve,
        "discard_emoji": args.discard,
        "approvers": approvers,    # human user ids (bot excluded); caller roster-checks
        "discarders": discarders,
        "bot_user": bot_user,
    }
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(out, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(description="Seed or poll approve/discard reactions on a review message.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("seed", "poll"):
        p = sub.add_parser(name)
        p.add_argument("ts", help="the review message timestamp (from post.py output)")
        p.add_argument("--channel", help="channel id (default SLACK_REVIEW_CHANNEL_ID / SLACK_TEST_CHANNEL_ID)")
        p.add_argument("--approve", default=APPROVE_EMOJI, help=f"approve emoji name (default {APPROVE_EMOJI})")
        p.add_argument("--discard", default=DISCARD_EMOJI, help=f"discard emoji name (default {DISCARD_EMOJI})")
        if name == "poll":
            p.add_argument("--json", action="store_true", help="pretty JSON output")
    args = ap.parse_args()

    if args.cmd == "seed":
        cmd_seed(args)
    else:
        cmd_poll(args)


if __name__ == "__main__":
    main()
