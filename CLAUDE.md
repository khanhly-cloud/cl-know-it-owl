# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

"Know-It-Owl" is a weekly **"Did you know?"** Slack post for CODE LEAP (channel
`#codeleap-home`). This is **not an app**: there is no server, no build, and no test
suite. The repo is a **human-reviewed library of approved facts** plus one posting
script. The whole safety guarantee ("no ex-employees, no conflicts, no unconfirmed
client work") rests on one invariant: nothing posts unless it was curated,
safety-filtered, and approved first.

## The one command that matters

All posting goes through a single script. **Never post by hand** (ad-hoc Slack calls
skip the bookkeeping and the safety guards):

    python3 slack/post.py <fact_file> [--to test|home] [--select] [--dry-run] [--record] [--no-customize]

- `--to test` (default) previews in the test channel and leaves the fact library untouched.
- `--to home` is the real weekly post. It sends the body verbatim, then records:
  stamps `posted_date`, appends to `post_history`, sets `status: posted`, and moves
  the file into `facts/posted/`.
- `--select` posts the oldest fact in `facts/approved/`.
- `--dry-run` prints the exact body and what it would record, sending and moving nothing.
- It refuses to send a non-approved fact to `#codeleap-home`, and refuses to repost
  identical wording (it hashes the body; see rotation below).

Slack credentials live in a git-ignored `.env` (keys: `SLACK_BOT_TOKEN`,
`SLACK_TEST_CHANNEL_ID`, `SLACK_HOME_CHANNEL` plus optional `SLACK_HOME_CHANNEL_ID`,
`SLACK_REVIEW_CHANNEL_ID`, `SLACK_SIGNING_SECRET`, `SLACK_TEAM_ID`, and optional
`SLACK_ICON_URL` / `SLACK_ICON_EMOJI`). Any direct Slack API call needs network
egress, which in this sandbox means running Bash with the sandbox disabled.

## Choosing what to post, and the fast-action commands

`post.py` sends but does not choose. `slack/pick.py` is the rotation engine it
lacks: it reads the library and decides **fresh vs recirculate** per
`config/rotation.md` (pool = `facts/approved/` plus `tier: core` facts in
`facts/posted/` past their `cooldown_weeks`; trivia never recirculates; aim for
~1 core refresher every 3 to 4 weeks). It is pure: no network, no file writes,
and prints JSON (`--json`) or a human summary. It never posts. (It is named
`pick.py`, not `select.py`: a module named `select` shadows the stdlib `select`
that `post.py` imports transitively, which breaks the import.)

One skill wraps the whole flow:

- **`/owl`** (`.claude/skills/owl/`): the single command, mode-selected by its
  argument. Runs `pick.py`, rewords a recirculated core fact in voice,
  safety-checks it, then routes every send through `post.py`. Modes:
  - default / `review` / `test`: REVIEW preview to the test channel (safe default).
  - `home`: the real weekly post to `#codeleap-home`. `dry`: dry run. `pick`: show
    the decision only. A fact path: use that exact fact.
  - `announce` / `resolve`: the autonomous mid-week reaction review. `announce`
    posts the candidate to a review channel; `resolve` acts on a human ✅ / 🗑️
    reaction (approve publishes via `post.py`, discard announces the next candidate).
  - `loop`: announce then poll the reaction itself every ~1 min, hands-off, until
    an approve publishes.

  `home` and `loop` must be explicit. Reaction primitives are in
  `slack/review.py`; setup, scopes, the review channel, and scheduling are in
  `slack/AUTONOMOUS.md`.

## Pipeline (read top to bottom)

    SOURCES -> HARVEST -> candidates/ -> (human approves) -> approved/ -> post.py --to home -> posted/

- `SKILL.md` is the operating manual: **HARVEST** (sources to candidate facts) and **POST**.
- A fact is one Markdown file with YAML frontmatter (`facts/SCHEMA.md`). It moves
  `facts/candidates/` -> `facts/approved/` -> `facts/posted/` as it progresses. The
  **body below the frontmatter is the exact Slack message, posted verbatim** (no label).
- `post_history` is a single-line JSON array maintained by `post.py`. Do not hand-edit
  `posted_date`, `status`, or `post_history`.

## Sources and the low-memory cache

- `config/sources.md` is the allow/deny list. Tier 1 is the leadership-approved Code
  Coffee decks on Google Drive (folder IDs are there). Tier 2 is a few curated Notion
  pages. Denylisted: HR, performance reviews, sales, and any client/project page.
  Client "firsts" and origin stories are held for leadership sign-off, never auto-published.
- Code Coffee decks are large PDFs read via the Google Drive connector (no local
  download). HARVEST caches a slim digest per deck to
  `sources/code-coffee/extracts.jsonl` (buckets: `safe`, `people`, `hold_clients`,
  `omit`) so decks are never re-OCR'd. Skip decks already cached.

## Hard rules (config/safety.md, config/persona.md, config/rotation.md)

- **Roster-check every name.** Anyone mentioned must be a current member (verify via
  Notion users / Slack users). Otherwise drop the name or the fact. Never reference
  departures, conflicts, HR, performance, pay, or unconfirmed clients.
- **Voice:** no em dashes ever; bold the words that matter; lead with the owl hook;
  about 2 emojis max; for a perk or policy show "How to use it"; one fact per post.
- **Rotation:** a fact is `tier: core` (evergreen; rotates back after `cooldown_weeks`,
  reworded each time) or `tier: trivia` (posted once). To re-run a core fact, edit its
  body to fresh wording; `post.py` blocks an exact-text repeat.

## Non-obvious gotchas

- The bot **cannot read the private test channel's history** (it has `channels:history`
  but the channel is private). It can only delete a message whose `ts` it captured at
  post time. A `chat.scheduleMessage` that already fired cannot be deleted by the bot,
  so post live when you might need to fix or remove a message.
- **Avatar consistency:** per-message `icon_emoji`/`username` is a costume, not the
  app's real profile, so messages can look inconsistent. The durable fix is to upload an
  app icon in Slack app settings and drop the overrides (or set `SLACK_ICON_URL`).
- The annual **health check-up** provider changes yearly: never name the provider.
- **Internal planning pages** (e.g. an event run-of-show) are source-only: cite them in
  a fact's `source`, do not link them in a post.
- **`post.py` does not enforce `cooldown_weeks`** (it only blocks an exact-wording
  repeat). Cooldown timing and the fresh-vs-recirculate choice are `slack/pick.py`'s
  job. `pick.py` is named to avoid shadowing the stdlib `select` module.
- **Reactions, not buttons.** Approve/Discard uses emoji reactions polled by a
  scheduled run, because Slack buttons and slash commands both need a public server
  (an Interactivity/Command Request URL) that this no-server repo avoids. See
  `slack/AUTONOMOUS.md`.
