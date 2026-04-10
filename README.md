# Follow Up Inbox — Telegram Bot

Never lose track of a Telegram message again.

Forward anything to this bot and it gets logged to a Google Sheet. When you're ready to action it, pull up your inbox with `/open`, mark things done, snooze them, or delete them.

---

## What it does

- **Capture** — forward any message (from any chat, channel, or DM) to the bot and it's logged instantly
- **Review** — `/open` shows everything waiting for your attention, with age flags so you can see what's overdue
- **Action** — mark items done, snooze to a specific time, or hard-delete them

All data lives in your own Google Sheet. No third-party servers hold your messages.

---

## Commands

| Command | What it does |
|---|---|
| `/start` | Setup guide |
| `/open` | List all open items |
| `/done 2` | Mark item 2 as done |
| `/snooze 2` | Snooze item 2 — bot asks until when |
| `/delete 2` | Permanently remove item 2 from the sheet |
| `/help` | Show command list |

**Age flags in `/open`:**
- 🔴 = item is more than 1 day old
- 🟠 = item is more than 4 hours old

Snoozed items automatically resurface in `/open` once their snooze time passes.

---

## Setup

You need three things: a Telegram bot token, a Google Sheet ID, and a Google service account credential.

### Step 1 — Create your Telegram bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the token it gives you — looks like `123456:ABC-DEF...`

### Step 2 — Create your Google Sheet

1. Go to [sheets.google.com](https://sheets.google.com) and create a new blank sheet
2. Name it anything you like
3. Copy the Sheet ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_IS_HERE/edit
   ```

### Step 3 — Create a Google service account

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or use an existing one)
3. Go to **APIs & Services → Library** and enable **Google Sheets API**
4. Go to **APIs & Services → Credentials → Create Credentials → Service Account**
5. Give it any name, click through to the end
6. Click the service account you just created → **Keys** tab → **Add Key → JSON**
7. Download the JSON file

### Step 4 — Share your sheet with the service account

1. Open the JSON file and find the `client_email` field — it looks like:
   ```
   your-bot@your-project.iam.gserviceaccount.com
   ```
2. Open your Google Sheet → Share → paste that email → set to **Editor** → Share

### Step 5 — Deploy to Railway

1. Fork or clone this repo
2. Create a new project at [railway.app](https://railway.app)
3. Connect your GitHub repo
4. Go to **Variables** and add:

   | Variable | Value |
   |---|---|
   | `TELEGRAM_BOT_TOKEN` | Your token from Step 1 |
   | `GOOGLE_SHEET_ID` | Your sheet ID from Step 2 |
   | `GOOGLE_CREDENTIALS_JSON` | The full contents of the JSON file from Step 3 (paste the whole thing) |

5. Railway will deploy automatically. The bot starts polling within seconds.

### Verify it's working

Open Telegram, find your bot, and send `/start`. It should reply with setup instructions.

Then forward any message to it — you should see "✅ Captured" and the message appears in your Google Sheet under a tab called **TelegramInbox**.

---

## Running locally

```bash
git clone https://github.com/YOUR_USERNAME/telegram-followup-inbox
cd telegram-followup-inbox

pip install -r requirements.txt

export TELEGRAM_BOT_TOKEN="your-token"
export GOOGLE_SHEET_ID="your-sheet-id"
export GOOGLE_CREDENTIALS_FILE="path/to/credentials.json"

python bot.py
```

The bot will log to stdout and tell you if any config is missing.

---

## Using the bot

### Capturing messages

Forward any message to the bot from a private chat. Or add the bot to a Telegram group named **"Follow Up Inbox"** — everything posted there gets logged automatically.

### Working your inbox

```
/open
```

Shows your numbered list of open items. Then:

```
/done 2        → marks item 2 as done
/snooze 2      → asks you until when, then hides it until that time
/delete 2      → permanently removes item 2 from the sheet
```

For `/snooze`, the bot will ask "Until when?" — reply with natural language:
- `tomorrow 9am`
- `3h`
- `Monday`
- `April 15 10am`

---

## Sheet structure

The bot writes to a worksheet called **TelegramInbox** with these columns:

| Column | What's in it |
|---|---|
| Timestamp (SGT) | When the message was captured, in Singapore time (UTC+8) |
| Originally From | Who sent the original message |
| Original Chat | Which chat it came from |
| Message | The message text |
| Has Media | Yes/No |
| Status | Open / Done / Snoozed |
| Notes | Timestamp when actioned, or snooze-until time |

The worksheet is created automatically if it doesn't exist.

---

## Troubleshooting

**Bot doesn't respond**
- Check Railway logs for startup errors
- Make sure all three env vars are set
- Confirm the bot token is correct (test with a fresh `/start`)

**"Log failed" error when forwarding**
- The service account doesn't have Editor access to the sheet — re-check Step 4
- The Sheet ID is wrong — double-check the URL

**Snooze time isn't understood**
- Try a more explicit format: `tomorrow 9am`, `2026-04-15 10:00`, or `in 3 hours`

**Items not resurfacing after snooze**
- Snoozed items reappear the next time you run `/open` after the snooze time passes — there's no push notification

---

## License

MIT — use it, modify it, sell your own version.
