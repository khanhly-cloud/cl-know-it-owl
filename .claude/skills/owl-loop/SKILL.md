---
name: owl-loop
description: >-
  Start the hands-off Know-It-Owl approval loop: a ~1-minute recurring poll that
  reads the ✅/🗑️ reaction on the in-flight review message and runs the preset
  resolve actions (approve -> publish via post.py --to home; discard -> announce
  the next candidate). Use after seeding reactions when you want the approval to
  resolve on its own without asking. Stops itself once an approve is published.
---

# /owl-loop: hands-off 1-minute poll + resolve loop 🦉

This is the "set it and forget it" wrapper the user presets after a review is
seeded. The reviewer clicks ✅ or 🗑️ whenever they like; this loop polls the
reaction every ~1 minute and runs the same resolve actions as `/owl-review
resolve`, with **no further prompting**. See `slack/AUTONOMOUS.md` for the flow
and `.review-state.json` shape.

**Cadence floor is 1 minute.** `CronCreate`'s minimum is one minute, so a "every
few seconds" ask becomes every 1 minute. Jobs are session-only (die when this
Claude session ends) and auto-expire after 7 days; for cross-session hands-off,
use the local cron in `slack/AUTONOMOUS.md` instead.

## Preconditions

1. Read `slack/.review-state.json`. If it is **missing**, there is no review in
   flight, so there is nothing to poll. Tell the user to run `/owl-review announce`
   (or `/owl-post`) first, then stop. Do NOT start a loop against no target.
2. `CronList` first: if an owl-loop cron is already running, do not create a
   second one. Report the existing job and stop.

## Start the loop

1. **Poll once now** (do not wait a full minute for the first check): run the
   **Resolve** steps below immediately. If that already approves + publishes,
   you are done, do not create the cron.
2. Otherwise create the recurring poll with `CronCreate`:
   - `cron`: `"* * * * *"` (every minute)
   - `recurring`: `true`
   - `prompt`: `"/owl-loop resolve-tick"` (see below)
   Report the returned job id and tell the user: the loop is live, they can react
   ✅ / 🗑️ any time, and it stops itself on an approve+publish (or they can say
   "stop the owl loop").

## Mode: resolve-tick (what each cron fire runs)

Each fire performs one non-interactive resolve pass. This is exactly the
`/owl-review resolve` logic, run without asking the user anything:

1. Read `slack/.review-state.json`. If absent, the review is already resolved:
   delete this cron (`CronDelete` with the job id) and stop.
2. Poll the reaction:

       python3 slack/review.py poll <ts> --json

3. Act on `verdict`:
   - **approve**: roster-check each id in `approvers` is a current member (Notion
     `notion-get-users` / Slack `users.list`); ignore non-members. If a real
     member approved, publish through the one script (network egress -> run Bash
     with the sandbox disabled):

           python3 slack/post.py <fact_file> --to home

     Then delete `slack/.review-state.json`, **`CronDelete` this loop's job**,
     and confirm the publish in thread. The week is done.
   - **discard**: add `fact_file`'s id to `discarded`, save state, and run
     `/owl-review announce` to post the next candidate and seed its reactions
     (update `.review-state.json` with the new `ts`). The loop keeps polling the
     new message on the next tick. If the walk is exhausted, post an owl note that
     the queue is empty, delete the cron, and stop.
   - **conflict**: both a human ✅ and 🗑️. Leave it; ping the reviewers in thread
     once to pick one. Keep polling.
   - **pending**: no human reaction yet (the bot's seeded reactions are excluded).
     Do nothing; keep polling.
   - **error**: usually `missing_scope` (`reactions:read`) or a private channel
     without `groups:history`. `CronDelete` the loop (do not spin forever on an
     error), report it, and point at `slack/AUTONOMOUS.md`.

## Stop it

`CronList` to find the job, then `CronDelete <id>`. The loop also deletes itself
on a successful approve+publish, on an exhausted queue, and on a hard Slack error.

## Guardrails (same as /owl-review)
- The home post ALWAYS goes through `slack/post.py`, never a direct Slack call.
- A human member must approve; `review.py poll` already excludes the bot's own
  seeded reaction, and this loop roster-checks the approver.
- Never leave a loop running against a missing `.review-state.json` or a repeating
  Slack error: delete the cron in those cases.
