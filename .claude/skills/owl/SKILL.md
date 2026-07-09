---
name: owl
description: >-
  The one Know-It-Owl command for the weekly "Did you know?" flow. Picks this
  week's fact (fresh vs recirculate via pick.py), rewords a recirculated core
  fact in voice, safety + roster checks it, and routes every send through
  slack/post.py. Modes: default/review preview to the test channel; `home` for
  the real post to #codeleap-home; `dry` for a dry run; `pick` to just show the
  decision; `announce`/`resolve` for the mid-week reaction review; `loop` for the
  fully hands-off announce-then-auto-publish flow. Default is a safe review
  preview: `home` and `loop` must be explicit.
---

# /owl: the Know-It-Owl weekly command 🦉

One entry point for the whole "Did you know?" pipeline: decide what to post,
reword it if it is a recirculated evergreen, safety-check it, and send it through
the single script. It can post directly, run the mid-week reaction review, or run
the whole thing hands-off.

**It never posts by hand.** Every send goes through `slack/post.py`, which keeps
the bookkeeping (posted_date, post_history, status, move to `facts/posted/`) and
the guards (approved-only to home, no exact-wording repeat). See `CLAUDE.md`.
`post.py` needs network egress, so run it with the sandbox disabled.

## Read the args (`$ARGUMENTS`)

Post modes (one-shot):
- empty, `review`, or `test` -> **REVIEW preview to the test channel (DEFAULT, safe).** Touches no files.
- `home` or `post` -> the real weekly post to `#codeleap-home` (records + moves the file).
- `dry` -> dry run: show the exact body and what it would record, send nothing.
- `pick` or `plan` -> just show the decision and stop (no reword, no post).
- a path like `facts/approved/2026-NN-foo.md` -> use that exact fact, skip the picker.

Review + hands-off modes (reaction-driven, see `slack/AUTONOMOUS.md`):
- `announce` -> post the next candidate to the **review** channel and seed ✅/🗑️.
- `resolve` -> read the reaction on the in-flight review and act on it once.
- `loop` -> announce (if nothing is in flight), then start a ~1-minute poll that
  auto-resolves with no further prompting. Stops itself on an approve+publish.
- `resolve-tick` -> internal: one non-interactive resolve pass (what each cron
  fire runs). Not meant to be typed by a human.

Default to the **review preview** whenever intent is unclear. The review gate is
ON by default (`config/rotation.md`): a human approves before anything reaches
home. `home` and `loop` must be explicit.

---

## Core: decide -> reword -> safety (shared by every mode)

Every mode starts here. `pick`/`plan` stops after step C1.

### C1. Decide what to post (no network)
Run the engine and read its JSON:

    python3 slack/pick.py --json

- `decision: "none"` -> the approved pool is empty. **Do NOT report "nothing to
  post" / "we are dry" and stop.** Go to **C0. Never go dry** below and keep
  looking for content. Only after C0 genuinely turns up nothing do you report,
  and then honestly ("I scanned the candidate queue, the Code Coffee decks, and
  the curated Notion pages and found nothing new that clears safety yet"), never
  as "the queue is empty".
- Otherwise note `pick.file`, `pick.type` (`fresh` | `recirculate`),
  `pick.needs_reword`, `pick.mentions_people`, `pick.source_type`,
  `pick.source_url`, `pick.current_body`. `walk` is the ordered fallback list
  (used by `announce` / the loop on discard).

If the user passed a fact path, use that file and treat it as `fresh` unless it
already lives in `facts/posted/` (then `recirculate`).

### C0. Never go dry: harvest before giving up
Whenever there is nothing to surface (a `decision: "none"` from `pick.py`, or the
review walk is exhausted after discards), **always look for more content** in this
order before you ever tell a human the queue is empty:

1. **Existing candidates.** Look in `facts/candidates/` for a fact not already in
   this cycle's `discarded` list. Run it through C3 (safety + roster). If one
   survives, surface **that** (it is a `candidate`, so it needs the ✅-promotion in
   the approve step below). Prefer the freshest / most intriguing.
2. **Harvest new content.** If `facts/candidates/` has nothing usable, run
   **HARVEST** (`SKILL.md` Operation A) over the allowlisted sources in
   `config/sources.md`: the **Code Coffee decks on Google Drive** (Tier 1) and the
   **curated Notion pages** (Tier 2). Draft new candidate records, safety-filter
   them (C3), write survivors to `facts/candidates/`, then take the best new one.
3. **Only if harvest also finds nothing new and safe** (all decks cached / no new
   safe nuggets) do you report, honestly and specifically, and stop. This is a
   real "sources exhausted right now" state, not a "queue empty" shrug.

Never invent a fact from nothing: everything still comes from an allowlisted
source and still passes safety. C0 changes *when* we harvest (proactively, on
demand, so we never run dry), not *what* we are allowed to post.

### C2. Reword (only if `needs_reword`, i.e. a recirculated core fact)
A `fresh` fact is post-ready: skip to C3. For a recirculate, the body MUST come
back in genuinely fresh wording (`config/rotation.md`: "same fact, fresh
outfit"). Read `config/persona.md`, `config/rotation.md`, `config/safety.md` in
full, then rewrite the body so that:

- It is a **different wording** from `pick.current_body` and every prior wording
  in `post_history`. Change the **hook, angle, scenario, and emoji**. `post.py`
  blocks a byte-identical repeat; clear the higher bar of reusing no prior wording.
- **Voice (hard rules):** no em dashes, ever (use periods, commas, colons,
  parentheses). Lead with `🦉 *Did you know...*`. **Bold the words that matter**
  (perk, number, action, policy name) with Slack `*...*`. About **2 emojis max**.
  One fact only. Short and skimmable.
- **Perk or policy** -> include a `*How to use it:*` line with the real next step
  (where to click, who to ask). No dead Slack commands: `/vacay`, `/resource`,
  `/request-access` work; **`/help` is dead**.
- **Read-more link:** `<source_url|Read more on CODE LEAP Home>` only when
  `source_type` is `notion` AND the source is not an internal planning page
  (run-of-show / agenda). If `safety.flags` says internal-only / "never link",
  omit it.
- Health check-up facts: **never name the provider** (it changes yearly).

Write the new body back into the same file, editing only the text below the
frontmatter. Do not touch `status`, `posted_date`, or `post_history`.

### C3. Safety re-check (always, fresh or reworded)
Before any send, re-verify against `config/safety.md`:

- **Roster-check names.** If `pick.mentions_people` is true (or the body names
  anyone), confirm each person is a current member via Notion `notion-get-users`
  and/or Slack `users.list`. Anyone who left, is not found, or is ambiguous ->
  remove the name or drop the fact. Do not post on doubt.
- No departures, conflicts, HR, performance, pay, or unconfirmed client/project
  claims. No confidential or internal-only material. Default to exclude when
  uncertain and surface it to the human instead of posting.

If any check fails, **stop and report** (or, in `announce`/loop, skip to the next
`walk` item). Do not post.

---

## Post modes: review / home / dry

After the core, print the exact body and the decision rationale (`pick.type`,
why, cooldown / cadence numbers), then send:

- review / default: `python3 slack/post.py <pick.file> --to test`
- dry run:          `python3 slack/post.py <pick.file> --to home --dry-run`
- real post:        `python3 slack/post.py <pick.file> --to home`

For a `fresh` pick going home the file is in `facts/approved/` (status
`approved`); `post.py` records it and moves it to `facts/posted/`. For a
`recirculate` pick the file is already in `facts/posted/` and it re-records in
place with the new wording.

**If C0 had to surface an unapproved `candidate`** (approved pool was empty), it
has no human approval yet, so it **cannot** go straight to `home` (`post.py` will
refuse a non-approved fact). Do not force it. Instead route it to **review**: post
it `--to test` and tell the user to approve it (react ✅ via `announce`/`loop`, or
promote it to `facts/approved/`) before it can publish. Only already-`approved` or
`posted`-core facts post directly to home.

Then **report**: previewed or posted, the channel, the captured `ts`, the
decision (fresh vs recirculate and why), whether fact files changed. If this was
a review preview, remind the user to run `/owl home` (or approve via `loop`) once
happy.

---

## Review modes: announce / resolve (reaction-driven, mid-week)

The no-server "Approve / Discard buttons": the reviewer reacts ✅ or 🗑️ on a
Slack message and a run acts on it. Needs `reactions:read` (+ `reactions:write`
to seed) and a review channel the bot can read; see `slack/AUTONOMOUS.md`. State
lives in `slack/.review-state.json` (`{ts, channel, fact_file, type, discarded}`);
a missing file means "no review in flight".

### Mode: announce (run mid-week)
1. Run the **core** (C1-C3). On `decision: "none"`, do **not** post a "nothing
   queued" note: run **C0 (Never go dry)** to pull an existing candidate or
   harvest fresh ones from Notion + Drive, and surface that. Only report if C0
   itself turns up nothing new and safe.
2. From `walk` (or the C0 candidate), take the first item whose `id` is **not** in
   the prior cycle's `discarded` list (read `.review-state.json` if present; fresh
   announce -> empty). If C3 safety fails for it, skip to the next item.
3. Post the candidate to the review channel as a preview (touches no fact files):

       python3 slack/post.py <fact_file> --to test

   Capture the `ts` it prints (`posted ok  ts=...`).
4. Seed the reactions so the reviewer just clicks:

       python3 slack/review.py seed <ts>

5. Write `slack/.review-state.json` with `{ts, channel, fact_file, type,
   discarded}` (carry the discarded list forward). Post a one-line owl prompt in
   thread: react ✅ to publish to #codeleap-home, 🗑️ to see another.

### Mode: resolve (run a day or two later, or on a poll schedule)
1. Read `slack/.review-state.json`. If absent, nothing to resolve; stop.
2. Poll the reaction:

       python3 slack/review.py poll <ts> --json

3. Act on `verdict`:
   - **approve**: roster-check each id in `approvers` is a current member (Notion
     `notion-get-users` / Slack `users.list`); ignore non-members. If a real
     member approved:
     - **Promote if it is still a candidate.** If `fact_file`'s `status` is
       `candidate` (a fact surfaced by C0 that was never pre-approved), the ✅ from
       a rostered member **is** the human approval: set `status: approved`, set
       `approved_by` to that member, and confirm `safety.roster_checked: true`.
       (A fact already `approved`/`posted` needs no promotion.)
     - Publish through the one script:

           python3 slack/post.py <fact_file> --to home

     `post.py` records it and enforces the approved-only + no-duplicate-wording
     guards, and moves the file to `facts/posted/`. Delete
     `slack/.review-state.json`, confirm in thread. Done for the week.
   - **discard**: add the current `fact_file` id to `discarded`, save state, and
     re-run **announce** to surface the next candidate. If the `walk` is exhausted,
     do **not** say the queue is empty: run **C0 (Never go dry)** to pull another
     existing candidate or harvest fresh ones from Notion + Drive, and announce
     that. Only report if C0 itself turns up nothing new and safe.
   - **conflict** (both ✅ and 🗑️ from humans): ping the reviewers in thread to
     pick one; leave it for the next run.
   - **pending** (no human reaction yet, bot's seeded reactions excluded): do
     nothing; leave it for the next run.
   - **error**: usually `missing_scope` (`reactions:read`) or a private channel
     without `groups:history`. Report it, point at `slack/AUTONOMOUS.md`, do not
     retry blindly.

---

## Hands-off mode: loop

The "set it and forget it" wrapper: announce this week's candidate, then poll the
reaction every ~1 minute and auto-resolve with **no further prompting**.

**Cadence floor is 1 minute** (`CronCreate`'s minimum). Jobs are session-only
(die when this Claude session ends) and auto-expire after 7 days. There is no
always-on, cross-session scheduler in this repo; the loop polls only while a
Claude session is alive (see `slack/AUTONOMOUS.md`).

1. `CronList` first: if an owl loop cron is already running, do not create a
   second one. Report the existing job and stop.
2. Read `slack/.review-state.json`:
   - **Present** -> a review is already seeded; skip to step 4 and poll that `ts`.
   - **Missing** -> run **announce** (above) to pick, safety-check, preview, seed,
     and write the state. Announce runs **C0** first, so it harvests from Notion +
     Drive rather than giving up; only if C0 is genuinely exhausted (nothing new
     and safe) does it find nothing, in which case stop (do not start a loop
     against nothing).
3. (announce done.)
4. **Poll once now** (do not wait a full minute): run **resolve-tick** (below)
   immediately. If that approves + publishes, you are done, do not create the cron.
5. Otherwise create the recurring poll with `CronCreate`:
   - `cron`: `"* * * * *"` (every minute)
   - `recurring`: `true`
   - `prompt`: `"/owl resolve-tick"`
   Report the job id and tell the user: the loop is live, they can react ✅ / 🗑️
   any time, it stops itself on an approve+publish (or they can say "stop the owl
   loop").

### Mode: resolve-tick (what each cron fire runs)
One non-interactive resolve pass, exactly the `resolve` logic run without asking
the user anything:

1. Read `slack/.review-state.json`. If absent, the review is resolved: `CronDelete`
   this job and stop.
2. `python3 slack/review.py poll <ts> --json`.
3. Act on `verdict` as in **resolve**, with these loop specifics:
   - **approve**: promote the fact first if its `status` is still `candidate`
     (set `status: approved` + `approved_by` = the reacting member), then
     `post.py ... --to home`, delete `.review-state.json`, **`CronDelete` this
     loop's job**, confirm in thread. The week is done.
   - **discard**: add to `discarded`, save, re-run **announce** (new `ts` in
     state); the loop keeps polling the new message next tick. If the `walk` is
     exhausted, run **C0 (Never go dry)** to surface another existing candidate or
     harvest fresh ones from Notion + Drive, and keep the loop alive on the new
     message. Only if C0 turns up nothing new and safe do you post that note,
     `CronDelete`, and stop.
   - **conflict** / **pending**: keep polling (ping once on conflict).
   - **error**: `CronDelete` the loop (do not spin on an error), report it, point
     at `slack/AUTONOMOUS.md`.

To stop the loop manually: `CronList` to find the job, then `CronDelete <id>`.

---

## Guardrails (do not break these)
- Never call the Slack API directly to post a fact. Always go through `post.py`.
- The single live post to `#codeleap-home` happens only on an approved fact and,
  in review/loop, only on a human member's ✅ (`review.py poll` excludes the bot's
  own seeded reaction; roster-check the approver). Previews go `--to test` only.
- Never set `status: approved` yourself, and never hand-edit `posted_date`,
  `status`, or `post_history` (`facts/SCHEMA.md`). Only `post.py` writes those.
- Default to a **review preview**, not a live post. `home` and `loop` are explicit.
- **Never report "we are dry" and stop.** On an empty pool or an exhausted walk,
  always run **C0**: check `facts/candidates/`, then HARVEST from Notion + Drive.
  Report only after C0 finds nothing new and safe, and say so specifically.
- A freshly harvested fact reaches `#codeleap-home` only through a rostered
  member's ✅ in the review channel, which promotes it to `approved` first. Do not
  auto-publish a `candidate` without that human ✅.
- If `pick.py` says `none`, do not invent a fact. Harvest from the allowlist first.
- Never leave a loop running against a missing `.review-state.json` or a repeating
  Slack error: `CronDelete` in those cases.
