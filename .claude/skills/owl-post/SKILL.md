---
name: owl-post
description: >-
  Fast action: decide and post this week's Know-It-Owl "Did you know?" fact. Runs
  the rotation engine (fresh vs recirculate), rewords a recirculated core fact in
  voice, safety-checks it, and routes through slack/post.py. Use for the weekly
  post, a quick review preview, a dry run, or "what would we post?". Default is a
  REVIEW preview to the test channel, never a live post unless you say "home".
---

# /owl-post: the fast-action weekly poster 🦉

One command that does the whole weekly decision: pick the fact, reword it if it is
a recirculated evergreen, safety-check it, and send it through the one script.

**It never posts by hand.** Every send goes through `slack/post.py`, which keeps
the bookkeeping (posted_date, post_history, status, move to `facts/posted/`) and
the guards (approved-only to home, no exact-wording repeat). See `CLAUDE.md`.

## Read the args (`$ARGUMENTS`)

- empty, `review`, or `test` -> **REVIEW preview to the test channel (DEFAULT).** Touches no files.
- `home` -> the real weekly post to `#codeleap-home` (records + moves the file).
- `dry` -> dry run: show the exact body and what it would record, send nothing.
- `pick` or `plan` -> just show the decision and stop (do not reword, do not post).
- a path like `facts/approved/2026-NN-foo.md` -> use that exact fact, skip the picker.

Default to **review** whenever intent is unclear. The review gate is ON by default
(`SKILL.md`, `config/rotation.md`): a human approves before anything reaches home.

## Steps

### 1. Decide what to post (no network)
Run the engine and read its JSON:

    python3 slack/pick.py --json

- `decision: "none"` -> tell the user there is nothing to post (`facts/approved/` is
  empty and no `core` fact is past its cooldown). Suggest running HARVEST
  (`SKILL.md` Operation A) to refill candidates. Stop.
- Otherwise note `pick.file`, `pick.type` (`fresh` | `recirculate`),
  `pick.needs_reword`, `pick.mentions_people`, `pick.source_type`,
  `pick.source_url`, and `pick.current_body`. The `walk` array is the ordered
  fallback list (used by the autonomous review loop on discard).

If the user passed a fact path, use that file instead and treat it as `fresh`
unless it already lives in `facts/posted/` (then treat it as `recirculate`).

### 2. Reword (only if `needs_reword`, i.e. a recirculated core fact)
A `fresh` fact is already post-ready: skip to step 3. For a recirculate, the body
MUST come back in fresh wording (`config/rotation.md`: "same fact, fresh outfit").
Read `config/persona.md`, `config/rotation.md`, `config/safety.md` in full, then
rewrite the body so that:

- It is a **genuinely different wording** from `pick.current_body` and from every
  prior wording. Change the **hook, the angle, the scenario, and the emoji**.
  `post.py` blocks a byte-identical repeat; you must clear the higher bar of not
  reusing any wording in the fact's `post_history`.
- **Voice (hard rules):** no em dashes, ever (use periods, commas, colons,
  parentheses). Lead with `🦉 *Did you know...*`. **Bold the words that matter**
  (the perk, the number, the action, the policy name) with Slack `*...*`. About
  **2 emojis max**. One fact only. Keep it short and skimmable.
- If it is a **perk or policy**, include a `*How to use it:*` line with the real
  next step (where to click, who to ask). Do not point at a dead Slack command:
  `/vacay`, `/resource`, `/request-access` work; **`/help` is dead** (memory).
- **Read-more link:** include `<source_url|Read more on CODE LEAP Home>` only when
  `source_type` is `notion` AND the source is not an internal planning page
  (run-of-show / agenda). If `safety.flags` says the source is internal-only or
  "never link", omit the link (memory: no-linking-internal-planning-pages).
- Health check-up facts: **never name the provider** (it changes yearly; memory).

Then **write the new body back into the same file** (the one in `facts/posted/`),
editing only the text below the frontmatter. Do not touch `status`, `posted_date`,
or `post_history`. `post.py` re-records the fact in place when you post it to home.

### 3. Safety re-check (always, fresh or reworded)
Before any send, re-verify against `config/safety.md`:

- **Roster-check names.** If `pick.mentions_people` is true (or the body names
  anyone), confirm each person is a current member via the Notion users API
  (`notion-get-users`) and/or Slack `users.list`. Anyone who left, is not found,
  or is ambiguous -> remove the name or drop the fact. Do not post on doubt.
- No departures, conflicts, HR, performance, pay, or unconfirmed client/project
  claims. No confidential or internal-only material. Default to exclude when
  uncertain and surface it to the human instead of posting.

If any check fails, **stop and report**; do not post.

### 4. Show, then route through the one script
Print the exact body and the decision rationale (`pick.type`, why, cooldown /
cadence numbers from the engine). Then send. **`post.py` needs network egress, so
run it with the sandbox disabled.**

- review / default: `python3 slack/post.py <pick.file> --to test`
- dry run:          `python3 slack/post.py <pick.file> --to home --dry-run`
- real post:        `python3 slack/post.py <pick.file> --to home`

For a `fresh` pick going home, the file is in `facts/approved/` (status `approved`)
and `post.py` records it and moves it to `facts/posted/`. For a `recirculate` pick
the file is already in `facts/posted/` (status `posted`, which `post.py` allows to
home) and it re-records in place with the new wording.

### 5. Report
Say what happened: previewed or posted, the channel, the captured `ts`, the
decision (fresh vs recirculate and why), and whether fact files changed. If this
was a review preview, remind the user to run `/owl-post home` (or react-approve via
the autonomous loop) once they are happy.

## Guardrails (do not break these)
- Never call the Slack API directly to post a fact. Always go through `post.py`.
- Never set `status: approved` yourself, and never hand-edit `posted_date`,
  `status`, or `post_history` (`facts/SCHEMA.md`). Only `post.py` writes those.
- Default to a **review preview**, not a live post. `home` must be explicit.
- If `pick.py` says `none`, do not invent a fact. Harvest first.
