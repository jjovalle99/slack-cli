# slack-cli

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org) [![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) [![ty](https://img.shields.io/badge/type%20checked-ty-blue)](https://github.com/astral-sh/ty) [![coverage](https://img.shields.io/badge/coverage-98%25-brightgreen)]()

Read-only Slack CLI for coding agents. All output is JSON to stdout.

![demo](demo.gif) Errors go to stderr as JSON. Every command accepts `--token` and `--cookie` flags to override credentials.

## Install

```
uv tool install .
```

> [!WARNING]
> This tool authenticates with unofficial `xoxc`/`xoxd` session tokens pulled from the Slack desktop app, not through OAuth. This means no app registration and no admin approval, but it also means your tokens have your full user permissions, Slack can revoke them at any time, and using them this way likely violates Slack's ToS. Treat your tokens like passwords. Don't share them.

## Credentials

This tool uses `xoxc`/`xoxd` session tokens extracted from the Slack desktop app instead of official API tokens (`xoxb`, `xoxp`). This means no Slack app creation, no OAuth flow, and no admin approval. It piggybacks on your existing desktop session. The tradeoff: these are unofficial, undocumented tokens. They can expire (on logout, password change, or admin session revocation) or break if Slack changes their internal format, and they carry whatever permissions the logged-in user has with no scoping.

## Auth

```
slack-cli auth
```

Extracts `xoxc`/`xoxd` tokens from the Slack desktop app (must be logged in). On macOS, triggers a system password prompt. Tokens are saved to `~/.config/slack-cli/config.json`. Token priority: `--token`/`--cookie` flags > `SLACK_XOXC_TOKEN`/`SLACK_XOXD_TOKEN` env vars > config file.

## Features

| I want to...                          | Command                                                        |
|---------------------------------------|----------------------------------------------------------------|
| Search messages by keyword            | `slack-cli search messages <query> [--limit N] [--public-only]`|
| Find a channel by name or topic       | `slack-cli search channels <query> [--limit N]`                |
| Find a user by name or email          | `slack-cli search users <query> [--limit N]`                   |
| Read a channel's message history      | `slack-cli read channel <channel_id> [--limit N] [--url URL]`  |
| Read all replies in a thread          | `slack-cli read thread <channel_id> <thread_ts> [--url URL]`   |
| Look up a user's full profile         | `slack-cli read user <user_id>`                                |
| Get channel metadata (topic, members) | `slack-cli read channel-info <channel_id>`                     |
| Read a canvas document as markdown    | `slack-cli read canvas <canvas_id>`                            |
| Download a file (image, doc, etc.)    | `slack-cli read file --url <url> [--output path]`              |
| List all visible channels             | `slack-cli list channels [--limit N]`                          |

Messages are returned with these fields: `text` (plain text, mrkdwn cleaned), `user` (resolved to real name), `ts`, `datetime` (ISO 8601), `thread_ts`, `channel`, `permalink`, `reactions`, `files`, `attachments`, `thread_refs` (links to other threads found in the message).

## Data Flow

Search commands return IDs that feed into read commands:

```bash
# 1. Search returns messages with `channel` (ID) and `ts` fields
slack-cli search messages "deployment issue"

# 2. Use those values to read the full thread
slack-cli read thread C07B2KQ0L15 1700000000.000000

# Or pass a Slack permalink directly
slack-cli read thread --url "https://myorg.slack.com/archives/C07B2KQ0L15/p1700000000000000"
```

Same pattern: `search channels` or `list channels` returns objects with an `id` field, which is the `channel_id` argument for `read channel`.

## Limitations

- Read-only. No posting, reacting, or modifying.
- `search channels` and `search users` fetch up to 500 items then filter client-side. In large workspaces, results may be incomplete.
- Rate limiting: retries once on 429, then raises.
- `auth` only works on macOS and Linux. Windows is unsupported because Slack stores its tokens in platform-specific locations (LevelDB + encrypted cookie DB) and the cookie decryption relies on macOS Keychain or Linux's hardcoded key. On Windows, you can skip `auth` entirely by providing tokens manually via `--token`/`--cookie` flags or `SLACK_XOXC_TOKEN`/`SLACK_XOXD_TOKEN` env vars.
