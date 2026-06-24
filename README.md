# 🦉 Know-It-Owl — CODE LEAP "Did you know?"

> The office know-it-all, but lovable and on a leash. 🦉

A weekly **"Did you know?"** post in `#codeleap-home` that surfaces CODE LEAP
history, milestones, fun facts, and how-we-work knowledge that newer team
members might not know yet.

The heart of this system is **not the bot** — it's a **human-reviewed library of
approved facts**. Nothing posts that wasn't curated and cleared first. That's the
safety mechanism behind the "no ex-employees / no conflicts / no unconfirmed
client work" rule.

## How it works

```
  SOURCES                HARVEST              REVIEW               POST
  ┌─────────────┐        ┌──────────┐         ┌──────────┐         ┌──────────────┐
  │ Code Coffee │  ───▶  │ extract  │  ───▶   │ human    │  ───▶   │ Know-It-Owl  │
  │ Notion      │        │ + safety │         │ 👍 / ✏️   │         │ posts weekly │
  │ (Slack)     │        │ filter   │         │ approve  │         │ #codeleap-   │
  └─────────────┘        └──────────┘         └──────────┘         │ home         │
                              │                     │              └──────────────┘
                         facts/candidates/    facts/approved/        facts/posted/
```

1. **Harvest** — scan approved sources, draft candidate facts, run them through
   the safety filter → `facts/candidates/`.
2. **Review** — a human approves (or edits) candidates → `facts/approved/`.
3. **Post** — once a week, the oldest approved fact is phrased by Know-It-Owl and
   sent to `#codeleap-home` → moved to `facts/posted/`.

## Status (2026-06-10)

- [x] Sources reachable & machine-readable: Google Drive (Code Coffee decks read
      via connector — **no local download needed**), Notion.
- [x] Bot installed & verified: **Know-It-Owl** (`knowitowl`, bot `B0BABEZBZJ4`)
      in workspace CODE LEAP (`T01REQX1UEB`). Scopes: `chat:write`,
      `chat:write.customize`, `channels:read`, `channels:history`, `users:read`.
- [x] Test post delivered to test channel `C0B9C9AP7PV` ✅.
- [ ] First harvest pass over Code Coffee decks + curated Notion → candidate facts.
- [ ] First review batch.
- [ ] First weekly post to `#codeleap-home`.

## Folder map

| Path | What it is |
|---|---|
| `SKILL.md` | The skill itself — harvest + post procedures. |
| `config/persona.md` | Know-It-Owl identity, voice, taglines. |
| `config/sources.md` | What we're allowed to read (allowlist) and what's off-limits (denylist). |
| `config/safety.md` | The safety filter every fact must pass. |
| `facts/SCHEMA.md` | The format of a single fact record. |
| `facts/candidates/` | Harvested, awaiting human review. |
| `facts/approved/` | Reviewed & cleared to post. |
| `facts/posted/` | Already sent, with date. |
| `slack/SETUP.md` | Bot scopes, install status, token handling, webhook fallback. |
| `slack/post.py` | The poster. Sends a fact verbatim and auto-updates the pipeline (posted_date, post_history, move to posted/). |
