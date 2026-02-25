# Discord to n8n Bot

Async `discord.py` bot that listens to one Discord channel and forwards messages to an n8n Webhook via HTTP POST using `aiohttp`.

## Important Concept

Discord Developer Portal is for bot/application configuration only (token, intents, OAuth permissions).  
This Python bot code runs locally on your machine or on your own host/server.

## Features

- Listens only to one configured guild and channel
- Ignores bot messages when `IGNORE_BOTS=true`
- Ignores empty/whitespace-only messages
- Sends message payload to n8n webhook as JSON
- Includes attachment URLs when present
- Retry logic for failed POSTs (3 attempts with backoff: `0.5s`, `1s`, `2s`)
- Friendly startup and forwarding logs

## Payload Sent to n8n

Each forwarded message includes:

- `content`
- `username`
- `user_id`
- `message_id`
- `channel_id`
- `guild_id`
- `timestamp` (ISO8601)
- `jump_url`
- `attachments` (list of URLs; empty list if none)

## Prerequisites

- Python 3.10+
- A Discord bot token
- Discord bot invited to your server/channel
- n8n instance with a Webhook node

## Discord Setup

### 1) Enable Message Content Intent

1. Open Discord Developer Portal.
2. Select your application → `Bot`.
3. Under `Privileged Gateway Intents`, enable `Message Content Intent`.
4. Save changes.

This must be enabled both in the portal and in code (already enabled in `bot/main.py`).

### 2) Get Guild and Channel IDs

1. In Discord app, go to `User Settings` → `Advanced`.
2. Turn on `Developer Mode`.
3. Right-click server → `Copy Server ID` (this is `DISCORD_GUILD_ID`).
4. Right-click channel → `Copy Channel ID` (this is `DISCORD_CHANNEL_ID`).

## n8n Setup

1. Create a workflow with a `Webhook` node (method: `POST`).
2. Copy either the Test URL or Production URL:
3. Use URL as `N8N_WEBHOOK_URL` in `.env`.

Notes:

- Test URL only works while `Listen for test event` is active in n8n.
- Production URL requires the workflow to be activated.

## Installation and Run

From project root (`discord_to_n8n_bot/`):

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create environment file:

```bash
cp .env.example .env
```

Fill in `.env` values:

```env
DISCORD_BOT_TOKEN=...
DISCORD_GUILD_ID=...
DISCORD_CHANNEL_ID=...
N8N_WEBHOOK_URL=...
IGNORE_BOTS=true
LOG_LEVEL=INFO
```

Run the bot:

```bash
python -m bot.main
```

## Troubleshooting

### Message content is empty

- `Message Content Intent` is likely disabled in Discord Developer Portal, or disabled in code.
- This project enables it in code; verify portal setting and restart bot.

### 401 / 403 / missing access

- Bot may not be invited to the target server.
- Bot may lack channel permissions (`View Channel`, `Read Message History`).
- Re-invite bot with required scopes/permissions.

### n8n webhook not receiving events

- If using Test URL, confirm `Listen for test event` is currently active.
- If using Production URL, confirm workflow is activated.
- Verify `N8N_WEBHOOK_URL` is correct.

### Rate limits

- Keep outbound behavior minimal.
- This bot only forwards relevant channel messages to n8n (one POST per message).
- Avoid adding extra Discord API calls in message handlers.

