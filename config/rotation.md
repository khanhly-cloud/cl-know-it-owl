# Rotation policy (repeat the important stuff, reworded)

Inspired by game loading-screen tips: the must-know things (benefits, policies,
how-tos) should resurface on a cycle, always in fresh wording, so new joiners
keep catching them and everyone is reminded how to actually use them. One-off
trivia is posted once and retired.

## Two tiers (set per fact via `tier:` in the schema)

- **core** (evergreen, important): benefits, policies, processes, how-tos.
  Rotates back periodically. Examples: WFH policy, Quarterly Team Event budget,
  PTO, referral bonus, meeting-room panel how-to, Slack commands, career ladder.
- **trivia** (one-off): history, milestones, fun moments, past events. Sent once.

## Cadence and mix

- One post per week.
- Aim for roughly **1 core refresher every 3 to 4 weeks**; the rest fresh.
- A `core` fact may not resurface until its `cooldown_weeks` have passed
  (suggested **8 to 12 weeks**, about quarterly). A newcomer then catches every
  must-know within a quarter, without veterans feeling nagged.
- Prefer never-posted facts first. As the unseen pool thins, lean more on the
  core rotation.

## Always rework the wording

When a core fact comes back, change the hook, the angle, the scenario, and the
emoji. Never reuse a wording stored in the fact's `post_history`. Same fact,
fresh outfit. Keep it interesting.

## Selection (each week)

1. Pool = `facts/approved/` (unseen) plus `facts/posted/` where `tier: core` and
   `weeks since posted_date >= cooldown_weeks`.
2. If a core fact is due and the cadence calls for a refresher, pick it and
   rework it. Otherwise pick the best fresh fact.
3. Post, stamp `posted_date`, and append the new variant to `post_history`.
