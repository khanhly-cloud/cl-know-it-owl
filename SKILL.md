---
name: did-you-know
description: >-
  Generate and post CODE LEAP "Did you know?" facts to Slack (#codeleap-home) as
  Know-It-Owl. Use when harvesting facts from approved sources (Code Coffee decks,
  curated Notion), when reviewing candidate facts, or when posting the weekly fact.
---

# Skill: "Did you know?" (Know-It-Owl 🦉)

Two operations: **harvest** (make candidate facts) and **post** (send the weekly
fact). Both obey `config/safety.md` and `config/sources.md`. Persona/voice from
`config/persona.md`. Fact format from `facts/SCHEMA.md`.

## Operation A — HARVEST (build the fact library)

Goal: turn approved sources into reviewable candidate facts.

1. Read `config/sources.md` for the current allowlist. **Never read denylisted
   sources** (HR, performance reviews, client/project pages, departed-staff
   content).
2. For each source in scope:
   - **Code Coffee decks** (Drive): read each PDF/PPTX **once** and cache a
     compact digest to `sources/code-coffee/extracts.jsonl` (low-memory). **Skip
     decks already cached.** Pull candidate nuggets from the cache, not the raw
     PDF (firsts, milestones, numbers, origins, traditions, how-we-work tidbits).
   - **Curated Notion** (when enabled): read only allowlisted pages.
3. For each nugget, draft a fact record per `facts/SCHEMA.md`.
4. Run **every** candidate through `config/safety.md`. Drop or flag anything that
   fails. When in doubt, exclude.
5. Write survivors to `facts/candidates/` (one file per fact). De-dupe against
   `facts/approved/` and `facts/posted/`.
6. Summarize the batch for the human: count, categories, anything flagged for a
   judgment call.

> This is the step to run as a multi-deck fan-out: one worker per deck extracting
> candidates, then a single safety + de-dupe pass over the merged set.

## Operation B — POST (the weekly fact)

1. **Select this week's fact** per `config/rotation.md`:
   - Pool = `facts/approved/` (unseen) plus `tier: core` facts in `facts/posted/`
     whose `cooldown_weeks` have elapsed.
   - Favor fresh facts, but on the rotation cadence (~1 in 3-4 weeks) pick a
     **core refresher** (a key benefit / policy / how-to) so newcomers keep
     seeing the must-knows. A human may also pick one directly.
2. Phrase it in Know-It-Owl's voice (`config/persona.md`): a punchy "Did you
   know…?" with a light owl touch. Keep it short and Slack-friendly.
3. **Review gate (default ON):** post the draft to the review channel / DM the
   curator first. Ship only on 👍. (Switch to auto-post only once trusted.)
4. **Post through the one script** (never post by hand):

       python3 slack/post.py <fact_file> --to home

   It sends the fact body verbatim as Know-It-Owl, then records automatically:
   stamps `posted_date`, appends to `post_history`, sets `status: posted`, and
   moves the file into `facts/posted/`. Use the default `--to test` to preview
   without touching the library, and `--dry-run` to see exactly what it will do.
   The script refuses to post unapproved facts to `#codeleap-home`, and refuses
   to repost identical wording.
5. To rotate a `tier: core` fact back later, edit its body to a **fresh wording**
   (the script blocks an exact-text repeat), then run the script again. `tier:
   trivia` facts stay retired in `facts/posted/`.

## Cadence

Weekly. MVP scheduling = a Claude Code scheduled task that runs Operation B.
Designed to graduate to an always-on hosted bot later with no change to the
fact library.
