# Fact record schema

One fact = one Markdown file with YAML frontmatter. Lives in `candidates/` →
`approved/` → `posted/` as it moves through the pipeline.

Filename: `YYYY-NN-short-slug.md` (e.g. `2026-01-first-code-coffee.md`).

```markdown
---
id: 2026-01-first-code-coffee
status: candidate        # candidate | flagged | approved | posted
category: history        # history | milestone | people | process | fun | culture
tier: trivia             # core = evergreen (benefits/policies/how-tos), rotates back | trivia = one-off
cooldown_weeks: 0        # core: min weeks before it may resurface (suggest 8-12); trivia: 0 (no repeat)
hook: "CODE LEAP has run a Code Coffee almost every month since 2023."
people_mentioned: []     # names referenced — each must pass the roster check
source:
  type: code_coffee      # code_coffee | notion | slack
  ref: "20230XYZ_CODE_COFFEE.pdf"
  url: "https://drive.google.com/file/d/.../view"
  date: "2023-XX-XX"
safety:
  roster_checked: false
  flags: []              # e.g. ["names a person — verify current"]
approved_by: ""          # filled at review time
posted_date: ""          # last time it was sent
post_history: []         # single-line JSON array, written by slack/post.py: [{date, channel, ts, hash}]
---

<the exact, post-ready Slack message in Know-It-Owl's voice. slack/post.py sends
this body VERBATIM, so write it as it should appear: lead with the owl hook, keep
it short (1 to 3 sentences), light owl touch, credit the source if it adds trust.
No extra label, no "Did you know?" wrapper.>
```

## Rules

- `hook` = the one-line essence (for scanning the library).
- The body below the frontmatter is the EXACT message posted verbatim by
  `slack/post.py` (no "Did you know?" label, no wrapper). Write it Slack-ready.
- Never hand-edit `posted_date`, `status`, or `post_history`. `slack/post.py`
  maintains them when you post. To rotate a core fact, change only its body wording.
- Any non-empty `people_mentioned` ⇒ `roster_checked: true` required before
  `status: approved`.
- Never set `status: approved` yourself. Only a human does that, at review time.
- `tier: core` facts (key benefits, policies, how-tos) rotate back periodically.
  They stay in `posted/` after sending and become eligible again only after
  `cooldown_weeks` have passed. `tier: trivia` facts are sent once.
- When a core fact resurfaces, **rework the wording** (new hook, new angle, new
  emoji). Never repeat a wording already in `post_history`; append the new one.
- See `config/rotation.md` for the full rotation and mix policy.
