---
name: owl-review
description: >-
  Autonomous mid-week review loop for Know-It-Owl. "announce" posts the week's
  candidate fact to the review channel and seeds Approve/Discard reactions;
  "resolve" reads the reaction and acts: approve posts it to #codeleap-home,
  discard automatically announces the next candidate. Built for a scheduled
  Claude routine. Requires the reactions scopes in slack/AUTONOMOUS.md.
---

# /owl-review: autonomous mid-week review loop 🦉

The no-server version of "Approve / Discard buttons": the reviewer just reacts
✅ or 🗑️ on a Slack message, and a scheduled run acts on it. Read
`slack/AUTONOMOUS.md` first: this needs `reactions:read` (+ `reactions:write` to
seed), a confirmed bot install, and a review channel the bot can read.

State for the in-flight review lives in `slack/.review-state.json`
(`{ts, channel, fact_file, type, discarded: [...] }`). Treat a missing file as
"no review in flight".

## Modes (`$ARGUMENTS`)

- `announce` (default) -> post the next candidate for review and seed reactions.
- `resolve` -> read the reaction on the in-flight review and act on it.

## Mode: announce  (run mid-week)

1. Run `python3 slack/pick.py --json`. If `decision: none`, post a short owl note
   to the review channel that there is nothing queued (suggest HARVEST) and stop.
2. From `walk`, take the first item whose `id` is **not** in the prior cycle's
   `discarded` list (read `slack/.review-state.json` if present; if this is a
   fresh announce, `discarded` is empty).
3. Prepare the body exactly as in **/owl-post** steps 2-3: reword it if
   `needs_reword` (recirculated core fact) following `config/persona.md` /
   `config/rotation.md` / `config/safety.md` (no em dashes, bold key words, owl
   hook, ~2 emoji, How-to-use-it, read-more unless internal-planning, no health
   provider, no dead slash commands), and run the full safety + roster check. If
   safety fails, skip to the next walk item.
4. Post the candidate to the review channel (the bot must be able to read it; see
   the runbook). This is a preview, so it touches no fact files:

       python3 slack/post.py <fact_file> --to test

   Capture the `ts` it prints (`posted ok  ts=...`).
5. Seed the reactions so the reviewer just clicks:

       python3 slack/review.py seed <ts>

6. Write `slack/.review-state.json` with `{ts, channel, fact_file, type,
   discarded}` (carry forward the discarded list). Post a one-line owl prompt in
   thread: react ✅ to publish to #codeleap-home, 🗑️ to see another.

## Mode: resolve  (run a day or two later, or on a poll schedule)

1. Read `slack/.review-state.json`. If absent, there is nothing to resolve; stop.
2. Poll the reaction:

       python3 slack/review.py poll <ts> --json

3. Act on `verdict`:
   - **approve**: roster-check each user id in `approvers` is a current member
     (Notion `notion-get-users` / Slack `users.list`); ignore reactions from
     non-members. If a real member approved, publish through the one script:

         python3 slack/post.py <fact_file> --to home

     `post.py` records it (posted_date, post_history, status, move to
     `facts/posted/`) and enforces the approved-only + no-duplicate-wording
     guards. Delete `slack/.review-state.json`. Confirm in thread. Done for the week.
   - **discard**: add the current `fact_file` id to `discarded`, save state, and
     re-run **announce** so the next candidate is posted automatically (this is
     the "on discard, another message" behavior). If `pick.py` / the walk is
     exhausted, post an owl note that the queue is empty and stop.
   - **conflict** (both ✅ and 🗑️ from humans) or **pending** (no human reaction
     yet): do nothing and leave it for the next resolve run, but if it is
     `conflict`, ping the reviewers in thread to pick one.
   - **error**: a Slack error (usually `missing_scope` for `reactions:read`, or a
     private channel without `groups:history`). Report it and point at
     `slack/AUTONOMOUS.md`; do not retry blindly.

## Guardrails
- The home post ALWAYS goes through `slack/post.py`, never a direct Slack call.
- Never auto-approve on the bot's own seeded reaction (`review.py poll` already
  excludes the bot user). A human member must react to approve.
- This loop only ever posts the review preview to a channel the bot can read; the
  single live post to `#codeleap-home` happens only on a human ✅.
