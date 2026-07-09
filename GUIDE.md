# 🦉 Know-It-Owl Operating Guide

How to run the weekly "Did you know?" post and the autonomous review loop, plus
what every command does. For the big picture see `README.md`; for the rules see
`CLAUDE.md`, `SKILL.md`, and `config/`.

## The pieces at a glance

| Command | What it does | Network? | Model (Claude)? |
|---|---|---|---|
| `slack/pick.py` | Decides **fresh vs recirculate** (the rotation engine). Prints the choice. Posts nothing. | No | No |
| `/owl` | The one command. Modes: default review preview, `home` real post, `dry`, `pick`, `announce`/`resolve` reaction review, `loop` hands-off. Rewords if needed, safety-checks, routes through `post.py`. | Yes (to post) | Yes (reword/safety) |
| `slack/post.py` | The **one sender**. Posts a fact verbatim and records the post (date, history, move to `posted/`). | Yes | No |
| `slack/review.py` | Reaction primitives: `seed` adds ✅/🗑️, `poll` reads the verdict. | Yes | No |

> **Network note (this environment):** any command that calls Slack needs network
> egress, which here means running it with the sandbox disabled. `pick.py` never
> touches the network, so it always runs normally.

---

## 0. One-time setup

### Slack credentials (`.env`, git-ignored)
| Key | Purpose |
|---|---|
| `SLACK_BOT_TOKEN` | The bot token (`xoxb-...`). Required. |
| `SLACK_TEST_CHANNEL_ID` | Where review previews go. |
| `SLACK_HOME_CHANNEL_ID` / `SLACK_HOME_CHANNEL` | The real `#codeleap-home`. |
| `SLACK_REVIEW_CHANNEL_ID` | Optional. The channel the autonomous loop posts to (falls back to `SLACK_TEST_CHANNEL_ID`). |
| `SLACK_ICON_URL` / `SLACK_ICON_EMOJI` | Optional avatar override (defaults to `:owl:`). |

### Bot scopes
Confirmed installed as **Know-It-Owl** (`knowitowl`) in workspace CODE LEAP. For
the **manual post** path you only need `chat:write`, `chat:write.customize`,
`channels:read`, `channels:history`, `users:read`.

For the **autonomous emoji review** you also need:
- `reactions:read` (read your ✅/🗑️)
- `reactions:write` (so the bot pre-seeds the ✅/🗑️; optional)
- `groups:history` (only if the review channel is **private**, which it is for our
  test channels)

Add scopes at api.slack.com/apps → Know-It-Owl → OAuth & Permissions → Bot Token
Scopes, then **Reinstall to Workspace** (may need a workspace admin to approve).
See `slack/SETUP.md` and `slack/AUTONOMOUS.md` for detail.

---

## 1. Where content comes from

A fact is one Markdown file: YAML frontmatter plus a body. **The body is the exact
Slack message, posted verbatim** (no label added). Files move:

```
facts/candidates/  ->  facts/approved/  ->  facts/posted/
  (harvested)          (human approved)     (already sent)
```

- **Harvest** (turn approved sources into candidate facts) and the field schema
  are documented in `SKILL.md` and `facts/SCHEMA.md`.
- A human promotes a candidate to `facts/approved/` by setting `status: approved`.
  Only a human does this.
- `tier: core` facts (benefits, policies, how-tos) recirculate after
  `cooldown_weeks`, reworded each time. `tier: trivia` is posted once.

---

## 2. Command reference

### `slack/pick.py`: the rotation engine
Decides what to post next. Pure: no network, no file changes. Prints the choice
and why.

```bash
python3 slack/pick.py                 # human-readable decision
python3 slack/pick.py --json          # machine-readable (used by /owl)
python3 slack/pick.py --core-every 4  # target weeks between core refreshers (default 3)
python3 slack/pick.py --today 2026-06-16 --root /tmp/fixture   # for testing
```

It returns one of three decisions:
- **fresh**: post the oldest unseen fact from `facts/approved/` (body is ready).
- **recirculate**: bring back a `core` fact from `facts/posted/` that is past its
  cooldown. This one **must be reworded** before posting.
- **none**: nothing is eligible (approved is empty and no core fact is due). Run a
  harvest to refill `candidates/`.

### `/owl`: the one command
Runs `pick.py`, rewords a recirculated core fact in Know-It-Owl's voice,
safety-checks it, then routes through `post.py`. One skill covers the fast weekly
post, the mid-week reaction review, and the fully hands-off loop.

| You type | It does |
|---|---|
| `/owl` | **Review preview** to the test channel (default, safe). |
| `/owl home` | The real post to `#codeleap-home` (records + moves the file). |
| `/owl dry` | Dry run: shows the body and what it would record, sends nothing. |
| `/owl pick` | Just shows the decision, posts nothing. |
| `/owl facts/approved/2026-NN-foo.md` | Use that exact fact, skip the picker. |
| `/owl announce` | Post the next candidate to the review channel and seed ✅/🗑️. |
| `/owl resolve` | Read the reaction once: ✅ publishes via `post.py`, 🗑️ announces the next candidate. |
| `/owl loop` | Announce, then poll the reaction every ~1 min and auto-resolve. Stops itself on approve+publish. |

Default is always the review preview. `home` and `loop` must be explicit. A human
must react; the loop ignores the bot's own seeded reactions and roster-checks the
approver.

### `slack/post.py`: the one sender
Never post by hand. Everything goes through this so the bookkeeping and guards
can't be skipped.

```bash
python3 slack/post.py --select --to home          # post the oldest approved fact, for real
python3 slack/post.py facts/approved/x.md --to home
python3 slack/post.py facts/approved/x.md          # test-channel preview (default)
python3 slack/post.py facts/approved/x.md --to home --dry-run
```

Flags: `--to test|home`, `--select` (oldest in `approved/`), `--record` (record
even on a test post), `--dry-run`, `--no-customize`. On a real post it stamps
`posted_date`, appends `post_history`, sets `status: posted`, and moves the file
to `facts/posted/`. It **refuses** to send a non-approved fact to home, and
**refuses** to repost identical wording (it hashes the body).

### `slack/review.py`: reaction primitives
The mechanical seed/poll used by the loop. No model needed.

```bash
python3 slack/review.py seed <ts> --channel C0XXXX            # add ✅ and 🗑️
python3 slack/review.py poll <ts> --channel C0XXXX --json     # read the verdict
```

`poll` prints a verdict: `approve`, `discard`, `conflict` (both from a human),
`pending` (no human reaction yet), or `error` (usually a missing scope). It
excludes the bot's own reactions, so only a real click counts.

---

## 3. The two ways to run it

### A. Manual weekly post (simplest)
1. `/owl` to preview this week's pick in the test channel.
2. Read it. If happy, `/owl home` to publish for real.

That's it. One person, two commands.

### B. Hands-off review by emoji (what the PoC tested)
1. `/owl announce` posts the candidate to the review channel and seeds ✅/🗑️.
2. A reviewer clicks **✅** (publish) or **🗑️** (skip) in Slack.
3. `/owl resolve` reads the reaction: ✅ publishes to `#codeleap-home`,
   🗑️ surfaces the next candidate automatically.

Steps 1 and 3 can be scheduled (e.g. announce Wednesday, resolve Thursday) so the
only human action is one emoji click. `/owl loop` chains both ends together and
polls the reaction itself, hands-off, until an approve publishes.

### C. Hands-off polling (`/owl loop`)
`/owl loop` announces the candidate and then polls the reaction every ~1 minute,
publishing on a human ✅ with no further prompting.

Caveat: this runs via `CronCreate`, which is **session-only**: it polls while a
Claude session is alive and auto-expires after 7 days. There is no always-on,
laptop-independent scheduler in this repo. An earlier OS-cron path
(`autorun.py` + `cron.sh`) was removed as dead code (its crontab pointed at a
stale directory and never ran); the cloud `/schedule` skill does not fit either,
since a cloud routine cannot reach this local-only repo or the git-ignored `.env`
token. See `slack/AUTONOMOUS.md`.

---

## 4. Safety and gotchas (the short list)
- **Roster-check every name** against current members before posting. Drop the
  name or the fact if anyone has left or cannot be verified.
- **Never** reference departures, conflicts, HR, performance, pay, or unconfirmed
  client work. Default to exclude when unsure. Full rules in `config/safety.md`.
- **Voice:** no em dashes, bold the key words, lead with the owl hook, about 2
  emojis, show "How to use it" for a perk or policy, one fact per post.
- **Never name the health check-up provider** (it changes yearly).
- **Internal planning pages** (run-of-show, agenda) are source-only: cite them,
  never link them in a post.
- **Post live, do not pre-schedule the home message.** A fired
  `chat.scheduleMessage` cannot be deleted by the bot.
- **`post.py` does not enforce `cooldown_weeks`** (only `pick.py` does) and only
  blocks an exact-wording repeat, so always reword a recirculated core fact.

---

## 5. Proof of concept (verified live)
The full no-server loop was tested end to end in the test channels:
post candidate → bot seeds ✅/🗑️ → human reacts ✅ → poll detects it (bot's own
reaction excluded) → approver roster-checked → fact published to the output
channel, with the hands-off version acting on a timer with no prompting. The only
gate before going live on `#codeleap-home` is wiring the production schedule
(section 3C) and rotating any token that was shared in plain text.
