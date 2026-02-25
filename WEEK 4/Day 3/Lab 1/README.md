# Week 4 - Day 3 - Lab 1

Discord message intake pipeline:

1. A local Python Discord bot listens to one Discord channel.
2. The bot sends each valid message to an n8n Webhook via HTTP POST.
3. n8n maps the payload and creates a new Airtable record.

## Project Structure

```text
WEEK 4/Day 3/Lab 1/
├── discord_to_n8n_bot/
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── logger.py
│   │   ├── main.py
│   │   └── webhook_client.py
│   ├── .env
│   ├── .env.example
│   ├── .gitignore
│   ├── README.md
│   └── requirements.txt
├── workflow/
│   └── Discord to Airtable Logger.json
└── screenshots/
```

## How It Works

- `bot/main.py` connects to Discord with message content intent enabled.
- It filters messages by:
- configured guild ID
- configured channel ID
- non-empty content (ignores whitespace-only messages)
- optional bot-message ignore (`IGNORE_BOTS=true`)
- For matching messages, it posts JSON to `N8N_WEBHOOK_URL` with retry logic (3 attempts, exponential backoff).
- The n8n workflow receives the webhook payload, maps fields, and creates a row in Airtable.

## Payload Sent to n8n

```json
{
  "content": "message text",
  "username": "author name",
  "user_id": "123456789012345678",
  "message_id": "123456789012345678",
  "channel_id": "123456789012345678",
  "guild_id": "123456789012345678",
  "timestamp": "2026-02-25T23:30:00+00:00",
  "jump_url": "https://discord.com/channels/.../...",
  "attachments": ["https://cdn.discordapp.com/..."]
}
```

## Prerequisites

- Python 3.10+
- Discord bot token
- Bot invited to target server and channel with read permissions
- n8n instance
- Airtable base/table ready for logs

## Setup

1. Create and activate virtual environment:

```bash
cd "WEEK 4/Day 3/Lab 1/discord_to_n8n_bot"
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create `.env` from template and fill values:

```bash
cp .env.example .env
```

Required variables:

- `DISCORD_BOT_TOKEN`
- `DISCORD_GUILD_ID`
- `DISCORD_CHANNEL_ID`
- `N8N_WEBHOOK_URL`
- `IGNORE_BOTS` (default: `true`)
- `LOG_LEVEL` (default: `INFO`)

## Run the Bot

From `discord_to_n8n_bot/`:

```bash
python -m bot.main
```

If needed, direct script execution also works:

```bash
python bot/main.py
```

## n8n Workflow Setup

1. In n8n, import:
- `workflow/Discord to Airtable Logger.json`
2. Open the `Webhook` node and confirm path is `discord-logger`.
3. Copy Webhook URL:
- Use **Test URL** when "Listen for test event" is active.
- Use **Production URL** when workflow is activated.
4. Put this URL in bot `.env` as `N8N_WEBHOOK_URL`.
5. Configure Airtable credentials in n8n and verify base/table mapping.

## Airtable Mapping

The workflow writes these fields:

- `Timestamp`
- `Client Name`
- `Channel`
- `Question`
- `Status`

Default `Status` is set to `New`.

## Test Plan

1. Start n8n webhook listener (test mode) or activate workflow (production mode).
2. Start the Python bot.
3. Send a message in the configured Discord channel.
4. Confirm:
- bot log shows forwarded message
- n8n execution receives payload
- Airtable gets new row

## Troubleshooting

- `ModuleNotFoundError: discord`
- install dependencies in the same Python environment used to run the bot.
- Bot starts but no content:
- ensure Message Content Intent is enabled in Discord Developer Portal and in code.
- `401/403` Discord errors:
- token invalid, bot not invited, or missing channel permissions.
- n8n receives nothing:
- wrong webhook URL, workflow inactive, or test listener not running.
- Airtable node fails:
- credentials not set or base/table/field mappings mismatch.

