# Safety filter

Every candidate fact must pass **all** checks before it can reach
`facts/candidates/`. Pre-approved Code Coffee content still passes through this as
a backstop. **Default to exclude when uncertain.**

## The checks

1. **No departed people.** If a fact names or clearly points to a specific person,
   verify they are a **current** CODE LEAP member (see roster check below). If they
   are not current, or you can't confirm, **drop the fact or remove the name**.
2. **No conflicts.** Nothing referencing disputes, disagreements, departures,
   reorgs, layoffs, or anything that could reopen a sore subject.
3. **No HR / performance / pay.** No reviews, ratings, salaries, promotions tied
   to individuals, hiring/firing.
4. **No unconfirmed client/project claims.** Client firsts, deal details, and
   project specifics are off-limits until leadership confirms (see
   `config/sources.md` → "Pending leadership sign-off").
5. **No confidential / internal-only material.** If it wasn't clearly meant to be
   shared company-wide, exclude it.
6. **Accurate & sourced.** Every fact cites where it came from. If you can't point
   to a source, it's not a fact — it's a guess. Drop it.
7. **Kind & inclusive.** Never at anyone's expense; no in-jokes that exclude newer
   members (the whole point is to *include* them).

## Roster check (for any person-mentioning fact)

- Pull current workspace members via the Notion users API (and/or Slack
  `users:read` once installed).
- Match the named person against that list.
- ✅ current member → ok to mention.
- ❌ not found / left / ambiguous → remove the name or drop the fact.

## On a judgment call

Don't guess. Mark the candidate `status: flagged` with a one-line reason and
surface it to the human in the harvest summary. A human decides.
