# Slack setup — Know-It-Owl 🦉

## Bot scopes (minimal set — text · read · delete · tag)

Added under **Bot Token Scopes** (api.slack.com/apps → Know-It-Owl → OAuth &
Permissions). None require the installing user to be a workspace admin.

| Scope | Purpose |
|---|---|
| `chat:write` | Send + edit + **delete Know-It-Owl's own** messages |
| `chat:write.customize` | Post under the owl name/avatar |
| `channels:read` | Resolve / read info about `#codeleap-home` |
| `users:read` | Look up users to @mention (tag) |

**Deferred** (add later, may trip admin approval): `channels:history`,
`groups:history` — only needed when we mine Slack for fun facts.

## Install status

⚠️ **Blocked at install.** Error: *"doesn't have a bot user to install."* Setting
the display name + bot scopes did not clear it, which indicates the **CODE LEAP
workspace requires admin approval to install apps** — and the current user is not
an admin (by design / confidentiality). Resolution options, in order:

1. **Webhook fallback (no bot user / often no admin):** OAuth & Permissions →
   *Incoming Webhooks* → On → *Add New Webhook to Workspace* → `#codeleap-home`.
   Gives a `hooks.slack.com/...` URL. Still posts as Know-It-Owl via payload
   (`username`, `icon_emoji`). One channel, no reading.
2. **Admin approval:** ask a Workspace Owner/Admin to approve/install Know-It-Owl
   with the four scopes above, then they hand over the **Bot User OAuth Token**
   (`xoxb-…`).
3. **Slack MCP connector (interim):** posts as the authorizing user, not the owl —
   fine for testing the pipeline end-to-end today.

## Token handling

- **Never commit tokens.** Put them in a local, git-ignored `.env`:
  ```
  SLACK_BOT_TOKEN=xoxb-...        # if bot install succeeds
  SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...   # if using webhook
  ```
- `.gitignore` already excludes `.env` and `*.token`.
- Don't paste tokens into chat — point me at the `.env` file instead.
