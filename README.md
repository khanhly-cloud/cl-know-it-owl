# 🦉 Know-It-Owl — CODE LEAP "Did you know?"

> The office know-it-all, but lovable and on a leash. 🦉

A weekly **"Did you know?"** post in `#codeleap-home` that surfaces CODE LEAP
history, milestones, fun facts, and how-we-work knowledge that newer team
members might not know yet.

The heart of this system is **not the bot** — it's a **human-reviewed library of
approved facts**. Nothing posts that wasn't curated, safety-filtered, and cleared
by a human first. That's the safety mechanism behind the "no ex-employees / no
conflicts / no unconfirmed client work" rule.

## How it works

```
  SOURCES                HARVEST              REVIEW               POST
  ┌─────────────┐        ┌──────────┐         ┌──────────┐         ┌──────────────┐
  │ Code Coffee │  ───▶  │ extract  │  ───▶   │ human    │  ───▶   │ Know-It-Owl  │
  │ Notion      │        │ + safety │         │ ✅ / 🗑️   │         │ posts weekly │
  │ (Slack)     │        │ filter   │         │ approve  │         │ #codeleap-   │
  └─────────────┘        └──────────┘         └──────────┘         │ home         │
        ▲                     │                     │              └──────────────┘
        │  never go dry       │                     │
        └─────────────────────┘              facts/candidates/ ─▶ facts/approved/ ─▶ facts/posted/
```

1. **Harvest** — scan approved sources, draft candidate facts, run them through
   the safety filter → `facts/candidates/`. Harvest is **proactive**: when the
   queue runs thin it goes back to Notion + Drive for fresh, intriguing facts
   rather than ever reporting "nothing to post."
2. **Review** — a human approves via an **✅ / 🗑️ reaction** in the review channel
   (or by editing a candidate) → `facts/approved/`. The ✅ is the human sign-off.
3. **Post** — once a week Know-It-Owl phrases the chosen fact and sends it to
   `#codeleap-home` → moved to `facts/posted/`. Core facts recirculate later,
   reworded; trivia posts once.

## The one command

Everything runs through a single skill, **`/owl`**, mode-selected by argument:

| You type | It does |
|---|---|
| `/owl` | Review preview to the test channel (safe default) |
| `/owl home` | The real weekly post to `#codeleap-home` |
| `/owl dry` / `/owl pick` | Dry run / show the decision only |
| `/owl announce` · `/owl resolve` | Post a candidate for review · act on the ✅/🗑️ |
| `/owl loop` | Announce, then auto-poll the reaction and publish on ✅ |

`home` and `loop` must be explicit. Every send routes through `slack/post.py`,
which keeps the bookkeeping and guards (approved-only to home, no repeat wording).
See `GUIDE.md` for the full command reference and `slack/AUTONOMOUS.md` for the
review loop.

## Status (2026-07-09)

- [x] Sources reachable & machine-readable: Google Drive (Code Coffee decks read
      via connector — **no local download needed**), Notion.
- [x] Bot installed & verified: **Know-It-Owl** (`knowitowl`, bot `B0BABEZBZJ4`)
      in workspace CODE LEAP (`T01REQX1UEB`). Scopes: `chat:write`,
      `chat:write.customize`, `channels:read`, `channels:history`, `users:read`.
- [x] Test post delivered to test channel `C0B9C9AP7PV` ✅.
- [x] First harvest pass over Code Coffee decks + curated Notion → candidate facts.
- [x] First review batch.
- [x] First weekly post to `#codeleap-home`.

**Live & running.** The whole pipeline is exercised end-to-end and the weekly
cadence is in motion. Facts are posting to `#codeleap-home` via `slack/post.py`
(7 posts recorded to home, latest 2026-07-01 — the seniority ladder). Currently
**1 fact approved and queued** (`facts/approved/2026-29-aws-partner.md`) and
**1 candidate awaiting review** (`facts/candidates/2026-5th-anniversary.md`).

### Recent improvements
- **One command.** Consolidated the three old skills (`owl-post`, `owl-review`,
  `owl-loop`) into a single mode-selected **`/owl`** skill. Simpler, less to keep
  in sync.
- **Never go dry.** The bot no longer reports "nothing to post." When the queue is
  thin or a candidate is discarded, it pulls from `facts/candidates/` and, failing
  that, **harvests fresh facts from Notion + Drive** on demand.
- **Approve by reaction.** A rostered member's **✅** in the review channel now
  counts as the human approval: it promotes a candidate to `approved` (recording
  `approved_by`) before posting. A human is still always in the loop.
- **Removed dead automation.** Deleted the broken OS-cron path
  (`autorun.py` + `cron.sh`, whose crontab pointed at a stale directory and never
  ran). Hands-off polling now runs via `/owl loop` (session-only; see the roadmap
  for always-on hosting).

## Folder map

| Path | What it is |
|---|---|
| `GUIDE.md` | Operating guide — every command, the two ways to run it, safety notes. |
| `SKILL.md` | The harvest + post procedures (the operating manual). |
| `CLAUDE.md` | Guidance and hard rules for Claude Code working in this repo. |
| `.claude/skills/owl/` | The **`/owl`** command — the single skill for the whole flow. |
| `config/persona.md` | Know-It-Owl identity, voice, taglines. |
| `config/sources.md` | What we're allowed to read (allowlist) and what's off-limits (denylist). |
| `config/safety.md` | The safety filter every fact must pass. |
| `config/rotation.md` | Fresh-vs-recirculate policy, cooldowns, the never-go-dry rule. |
| `facts/SCHEMA.md` | The format of a single fact record. |
| `facts/candidates/` | Harvested, awaiting human review. |
| `facts/approved/` | Reviewed & cleared to post. |
| `facts/posted/` | Already sent, with date + history. |
| `slack/pick.py` | The rotation engine: decides fresh vs recirculate. Pure, posts nothing. |
| `slack/post.py` | The one poster. Sends a fact verbatim and updates the pipeline (posted_date, post_history, move to posted/). |
| `slack/review.py` | Reaction primitives: seed ✅/🗑️, poll the verdict. |
| `slack/SETUP.md` | Bot scopes, install status, token handling. |
| `slack/AUTONOMOUS.md` | The review-by-reaction loop: scopes, review channel, going live. |

## Roadmap — where Know-It-Owl goes next

Today Know-It-Owl is a **one-way, human-in-the-loop broadcaster** driven from a
Claude Code session: it harvests, a human ✅s, it posts. The next chapter is to
make it a **two-way, always-on, more autonomous teammate**. The three tracks below
build on each other — hosting is the foundation that unlocks the other two.

### 1. In-channel interactivity (talk back to users)
Move from broadcast to conversation. Let people **@mention Know-It-Owl** or reply
in-thread and get a useful response: "tell me more about that," "got any fact
about our WFH policy?", "who do I ask about X?", or a `/didyouknow` on demand.
- **What it needs:** the Slack **Events API** (`app_mention`, `message.channels`)
  and/or **Socket Mode**, an interactivity request URL, and new scopes
  (`app_mentions:read`, `im:history`). Answers still come from the approved fact
  library + safety filter, never freeform, so the safety guarantee holds.
- **Why:** turns a weekly post into an everyday knowledge companion, and gives us
  a natural channel for people to *request* topics (which feeds harvest).

### 2. Host on AWS (always-on, laptop-independent)
Today `/owl loop` is **session-only** (dies with the Claude session) and the old
OS-cron path was removed as dead code. To run unattended we need real hosting.
- **What it needs:** e.g. **Lambda + EventBridge** for the scheduled weekly post
  and mid-week review poll (zero idle cost), or a small **ECS/Fargate** service if
  we want a persistent Socket-Mode listener for track 1. Secrets move from the
  git-ignored `.env` into **AWS Secrets Manager / SSM**; the fact library lives in
  the repo (or S3/DynamoDB if we outgrow files); logs to **CloudWatch**.
- **Why:** the prerequisite for both real interactivity and real autonomy — the
  bot can't respond to messages or run on schedule if nothing is listening.

### 3. Bot autonomy (fewer human touchpoints, same safety)
Shrink the manual steps while keeping a human accountable for anything sensitive.
- **What it could do:** auto-harvest on a schedule, auto-reword recirculated core
  facts, self-select and pre-stage the weekly candidate, and learn from ✅/🗑️
  patterns over time. Possibly **auto-approve low-risk trivia** while still holding
  anything naming people, clients, or "firsts" for explicit human sign-off.
- **The invariant to protect:** *nothing sensitive posts without a human.* Autonomy
  should reduce clicks, not remove the safety gate. Every relaxation needs an
  explicit guardrail (roster check, denylist, leadership hold) kept in `config/`.

> Sequencing: **AWS hosting first** (foundation), then **interactivity** and
> **autonomy** in parallel on top of it.
