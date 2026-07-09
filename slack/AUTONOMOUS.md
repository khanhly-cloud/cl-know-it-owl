# Autonomous mid-week review (Part B runbook)

Goal: once a week, mid-week, Know-It-Owl posts the next "Did you know?" candidate
to a review channel for one human to approve or discard. Approve publishes it to
`#codeleap-home`; discard automatically surfaces the next candidate. No server.

## Why reactions, not buttons or slash commands

Slack interactive **buttons** and **slash commands** both require an
**Interactivity / Command Request URL**: a public, always-on HTTPS server that
catches the click, verifies `SLACK_SIGNING_SECRET`, and replies in 3 seconds. This
repo is deliberately "not an app: no server, no build" (`CLAUDE.md`), so we use
**emoji reactions** instead: the reviewer clicks ✅ or 🗑️ on the message, and a
scheduled run reads the reaction and acts. Same human experience, zero hosting.

If you ever decide to host a server, buttons are the better upgrade (one click,
richer UI) and beat slash commands (which make the reviewer type). Until then,
reactions are the only path that keeps the no-server guarantee.

## The loop

```
  (mid-week, scheduled)            (a day or two later, scheduled or polled)
  /owl announce                    /owl resolve
     pick.py  -> choose fact          review.py poll <ts>
     reword (if recirculate)            approve -> post.py --to home  (records + moves)
     safety + roster check              discard -> announce next candidate (loop)
     post.py --to test  (preview)       conflict/pending -> wait, ping reviewers
     review.py seed <ts>  (✅ 🗑️)
     save slack/.review-state.json
```

The single live post to `#codeleap-home` only ever happens through `slack/post.py`
on a human ✅. Everything before that is a preview in a channel the bot can read.

## Enable it (the parts you control)

1. **Confirm the bot is really installed.** `README.md` says it is; `slack/SETUP.md`
   says install was "Blocked at install" (workspace needs admin approval, and the
   installing user is not an admin). Settle this first. Quick check: a test preview
   that actually sends,

       python3 slack/post.py facts/candidates/<some>.md --to test

   (run with the sandbox disabled for network egress). If it returns `posted ok
   ts=...`, the token works.

2. **Add two scopes** in the Slack app config (OAuth & Permissions -> Bot Token
   Scopes), then reinstall the app:
   - `reactions:read`  (required, for `review.py poll`)
   - `reactions:write` (only if the bot should seed the ✅/🗑️; a human can also
     react cold, in which case skip the seed step)
   Adding scopes may hit the same admin-approval wall noted in `SETUP.md`.

3. **Pick a review channel the bot can read.** The bot has `channels:history`, so a
   **public** review channel works out of the box (it can read reactions there).
   A **private** channel additionally needs `groups:history` and the bot invited.
   Do not reuse the existing private test channel for polling unless you add
   `groups:history` (the bot cannot read private history today; see `CLAUDE.md`).
   Set the channel in `.env`:

       SLACK_REVIEW_CHANNEL_ID=C0XXXXXXX   # falls back to SLACK_TEST_CHANNEL_ID

4. **Run it.** Drive the loop through the `/owl` skill (Claude-driven, so it can
   reword a recirculated core fact, which a pure-Python runner cannot):
   - `/owl announce` mid-week, then `/owl resolve` a day or two later, or
   - `/owl loop` to announce and then auto-poll the reaction every ~1 minute
     until a human ✅ publishes.

   Note `/owl loop` uses `CronCreate`, which is **session-only**: it polls while a
   Claude session is alive and auto-expires after 7 days. There is no
   always-on/laptop-independent scheduler here. The cloud `/schedule` skill does
   not fit either: a cloud routine cannot reach this local-only repo or the
   git-ignored `.env` token, and there is no Slack connector. (A previous local
   `cron` + `autorun.py` path was removed as dead code: its crontab pointed at a
   stale directory and never ran.)

## Going live: flip the .env channels

`.env` may still be PoC-pointed: review previews to the PoC review channel and
"home" to a PoC output channel (via a `SLACK_HOME_CHANNEL_ID` override), so a run
would NOT post to real `#codeleap-home`. To go live:
- Set `SLACK_HOME_CHANNEL_ID` to the real `#codeleap-home` id (or remove it so
  `post.py` falls back to `SLACK_HOME_CHANNEL`).
- Set `SLACK_TEST_CHANNEL_ID` / `SLACK_REVIEW_CHANNEL_ID` to the real readable
  review channel.
- `announce` no longer stops when `facts/approved/` is empty: it runs **C0**
  (`/owl` skill) to surface a candidate or harvest fresh facts from Notion +
  Drive. It only reports when that scan is genuinely exhausted.

## Gotchas (from CLAUDE.md / memory)

- **Post live, do not schedule the home message.** A `chat.scheduleMessage` that
  already fired cannot be deleted by the bot, and the bot can only delete a message
  whose `ts` it captured. So the home post is sent live by `post.py` on approval,
  never pre-scheduled.
- **Capture the review `ts`.** `post.py` prints it; `/owl` stores it in
  `slack/.review-state.json` so `resolve` and any later delete/replace can use it.
- **Never bypass `post.py`** for the home post. It is the only thing that stamps
  `posted_date`, appends `post_history`, sets `status: posted`, moves the file, and
  blocks duplicate wording / non-approved facts.
- **A human must approve.** `review.py poll` excludes the bot's own seeded
  reaction, and `/owl` roster-checks the approver. The poll is the courier,
  not the approver: the safety guarantee still rests on a human ✅.

## Files

- `slack/pick.py` decides fresh vs recirculate (no network, no writes).
- `slack/review.py` seeds and polls the ✅/🗑️ reactions.
- `slack/post.py` is the one sender and bookkeeper (unchanged).
- `.claude/skills/owl/` is the one command: `/owl` for the manual fast-action post,
  `/owl announce`/`resolve` for this autonomous loop (Claude-driven; handles
  rewording), and `/owl loop` for the hands-off poll.
- `slack/.review-state.json` (created at runtime) holds the in-flight review.
