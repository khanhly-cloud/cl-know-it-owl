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
  /owl-review announce             /owl-review resolve
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

4. **Schedule it.** Do NOT use the cloud `/schedule` skill here: a cloud routine
   cannot reach this local-only repo or the git-ignored `.env` token, and there is
   no Slack connector. Use **local cron** with the mechanical `slack/autorun.py`
   (pure Python, no Claude for the common case). Suggested cadence: `announce`
   mid-week, `resolve` a few times over the next day during hours the machine is on.
   See **Deployed setup** below for the exact crontab that is installed.

## Deployed setup (local cron on this machine)

This is wired up and running as **local cron**, not the cloud `/schedule` skill.
The cloud option was ruled out: a cloud routine cannot see this local-only repo or
the git-ignored `.env` token, and there is no Slack connector. Local cron runs on
the machine where the repo and token already live.

**Mechanical, no Claude.** The cron runs `slack/autorun.py`, which reuses
`pick.py` + `post.py` + `review.py` in pure Python: zero tokens, nothing to keep
open. A recirculated `core` fact needs a reworded body, which autorun cannot
generate, so on those weeks `announce` posts a heads-up to run `/owl-post` by hand.

- `slack/autorun.py announce` picks a fact; if FRESH, posts it to the review
  channel and seeds ✅/🗑️ (writes `slack/.review-state.json`). If the pick needs a
  reword, it posts a heads-up and stops.
- `slack/autorun.py resolve` polls the in-flight review and acts: ✅ roster-checks
  the approver then `post.py --to home` (records + moves); 🗑️ announces the next
  candidate; pending/conflict are left for the next run.
- `slack/cron.sh announce|resolve` is the wrapper cron calls: it `cd`s into the
  repo, runs autorun with `/usr/bin/python3`, and logs to `/tmp/owl-cron.log`.

Installed crontab (local Asia/Saigon time; edit with `crontab -e`):

    30 11  * * 3   ".../slack/cron.sh" announce   # Wed 11:30: announce
    0 13-17 * * 3  ".../slack/cron.sh" resolve     # Wed 1-5pm hourly: resolve
    0 9-17  * * 4  ".../slack/cron.sh" resolve      # Thu 9am-5pm hourly: resolve

(The path is the full repo path; resolve is a harmless no-op when nothing is in
flight, so running it hourly is cheap.)

### macOS gotcha: Full Disk Access (required, or it silently fails)
The repo lives in `~/Desktop`, which macOS protects (TCC). `cron` cannot read it
until you grant access: **System Settings -> Privacy & Security -> Full Disk
Access -> add `/usr/sbin/cron`**. Without this the jobs run but fail to read the
repo and `.env`. Moving the repo out of `~/Desktop` also avoids it.

### Currently PoC-pointed (flip before going live)
`.env` sends review previews to the PoC review channel and "home" to the PoC
output channel (via a `SLACK_HOME_CHANNEL_ID` override), so cron will NOT post to
real `#codeleap-home`. To go live:
- Set `SLACK_HOME_CHANNEL_ID` to the real `#codeleap-home` id (or remove it so
  `post.py` falls back to `SLACK_HOME_CHANNEL`).
- Set `SLACK_TEST_CHANNEL_ID` / `SLACK_REVIEW_CHANNEL_ID` to the real readable
  review channel.
- Make sure `facts/approved/` actually has facts, or `announce` just logs
  "nothing to post".

### Operate it
- Watch: `tail -f /tmp/owl-cron.log`
- Test now: `slack/cron.sh announce` or `slack/cron.sh resolve`
- Edit or remove: `crontab -e` (the block is labeled).

## Gotchas (from CLAUDE.md / memory)

- **Post live, do not schedule the home message.** A `chat.scheduleMessage` that
  already fired cannot be deleted by the bot, and the bot can only delete a message
  whose `ts` it captured. So the home post is sent live by `post.py` on approval,
  never pre-scheduled.
- **Capture the review `ts`.** `post.py` prints it; `/owl-review` stores it in
  `slack/.review-state.json` so `resolve` and any later delete/replace can use it.
- **Never bypass `post.py`** for the home post. It is the only thing that stamps
  `posted_date`, appends `post_history`, sets `status: posted`, moves the file, and
  blocks duplicate wording / non-approved facts.
- **A human must approve.** `review.py poll` excludes the bot's own seeded
  reaction, and `/owl-review` roster-checks the approver. The cron is the courier,
  not the approver: the safety guarantee still rests on a human ✅.

## Files

- `slack/pick.py` decides fresh vs recirculate (no network, no writes).
- `slack/review.py` seeds and polls the ✅/🗑️ reactions.
- `slack/post.py` is the one sender and bookkeeper (unchanged).
- `slack/autorun.py` is the mechanical cron runner (announce/resolve, no Claude).
- `slack/cron.sh` is the cron wrapper (logs to `/tmp/owl-cron.log`).
- `.claude/skills/owl-post/` is the manual fast-action command.
- `.claude/skills/owl-review/` is this autonomous loop (Claude-driven; handles rewording).
- `slack/.review-state.json` (created at runtime) holds the in-flight review.
