# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Telegram bot that logs messages from Telegram conversations into a Google Sheet, which feeds into Claude's daily brief system. Users forward messages to the bot (or send them in a group called "Follow Up Inbox"), then manage them via `/open`, `/done`, and `/snooze` commands.

## Running the Bot

```bash
pip install -r requirements.txt

export TELEGRAM_BOT_TOKEN="..."
export GOOGLE_SHEET_ID="..."
# Use either a file path or a JSON string for credentials:
export GOOGLE_CREDENTIALS_FILE="credentials.json"   # default
# OR
export GOOGLE_CREDENTIALS_JSON='{"type":"service_account",...}'  # for cloud deployments

python bot.py
```

There are no tests and no build step. The Procfile (`worker: python bot.py`) is for Railway/Heroku deployment.

## Architecture

The entire application is `bot.py` (256 lines). It uses `python-telegram-bot` in polling mode (not webhooks).

**Data flow:**
1. Telegram message received → `handle_message()` filters to DMs or groups named "Follow Up Inbox"
2. Metadata extracted (sender, original chat for forwards, timestamp in SGT/UTC+8, media flag)
3. Row appended to "TelegramInbox" worksheet in the configured Google Sheet
4. User issues `/open` → `/done N` or `/snooze N` to update row Status column

**Google Sheets as the database:** `get_sheet()` opens the sheet and auto-creates the "TelegramInbox" worksheet with headers if missing. Columns: Timestamp, From, Chat, Message, Media, Status, Notes.

## Key Design Details

- **Timezone is hardcoded to SGT (UTC+8)** — timestamps stored and displayed in Singapore time
- **Credential loading**: tries `GOOGLE_CREDENTIALS_JSON` env var first (JSON string), falls back to file at `GOOGLE_CREDENTIALS_FILE` (default: `credentials.json`)
- **Message filtering**: only logs messages from private chats or groups whose title is exactly "Follow Up Inbox"
- **Forward attribution**: extracts original sender from Telegram forward metadata (`forward_origin`) — handles user forwards, channel forwards, and direct notes
- **Age-based flags in `/open`**: 🔴 = 1+ day old, 🟠 = 4+ hours old (calculated from stored ISO timestamp)
- **Status values**: `"Open"`, `"Done"`, `"Snoozed"` — `/open` command only shows rows where Status == "Open"
