# Follow Up Inbox — Telegram Bot

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.com/deploy/telegram-follow-up-inbox-bot)

Never lose track of a Telegram message again.

Forward anything to this bot and it's saved to your inbox. When you're ready to action it, pull up your list with `/open`, mark things done, snooze them, or delete them. Everything is per-user — each person who uses the bot has their own private inbox.

---

## What it does

- **Capture** — forward any message (from any chat, channel, or DM) to the bot and it's logged instantly
- **Review** — `/open` shows everything waiting for your attention, with age flags so you can see what's overdue
- **Action** — mark items done, snooze to a specific time, or hard-delete them
- **Multi-user** — each Telegram user has their own isolated inbox

---

## Commands

| Command | What it does |
|---|---|
| `/start` | Welcome message |
| `/open` | List your open items |
| `/done 2` | Mark item 2 as done |
| `/snooze 2` | Snooze item 2 — bot asks until when |
| `/delete 2` | Permanently remove item 2 |
| `/help` | Show command list |

**Age flags in `/open`:**
- 🔴 = item is more than 1 day old
- 🟠 = item is more than 4 hours old

Snoozed items automatically resurface in `/open` once their snooze time passes.

---

## Setup (for the bot operator)

You host one instance. Users just message the bot — no setup on their end.

### Step 1 — Create your Telegram bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the token — looks like `123456:ABC-DEF...`

### Step 2 — Create a Supabase project

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Once created, go to **SQL Editor** and run the contents of `schema.sql` in this repo
3. Go to **Project Settings → API** and copy:
   - **Project URL** → your `SUPABASE_URL`
   - **service_role** secret key → your `SUPABASE_KEY` (use service_role, not anon)

### Step 3 — Deploy to Railway

1. Fork or clone this repo
2. Create a new project at [railway.app](https://railway.app) and connect your GitHub repo
3. Go to **Variables** and add:

   | Variable | Value |
   |---|---|
   | `TELEGRAM_BOT_TOKEN` | From Step 1 |
   | `SUPABASE_URL` | From Step 2 |
   | `SUPABASE_KEY` | From Step 2 |

4. Railway deploys automatically. The bot starts within seconds.

### Verify it's working

Open Telegram, find your bot, and send `/start`. It should reply with a welcome message.

Then forward any message to it — you should see "✅ Captured", and the row appears in your Supabase `inbox` table.

---

## Running locally

```bash
git clone https://github.com/YOUR_USERNAME/telegram-followup-inbox
cd telegram-followup-inbox

pip install -r requirements.txt

export TELEGRAM_BOT_TOKEN="your-token"
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-service-role-key"

python bot.py
```

The bot will log to stdout and exit with a clear error if any config is missing.

---

## Using the bot (end user)

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
/delete 2      → permanently removes item 2
```

For `/snooze`, the bot will ask "Until when?" — reply with natural language:
- `tomorrow 9am`
- `3h`
- `Monday`
- `April 15 10am`

---

## Database schema

One table in Supabase: `inbox`

| Column | Type | What's in it |
|---|---|---|
| id | bigserial | Auto-increment primary key |
| user_id | bigint | Telegram user ID — each user's data is isolated |
| timestamp | timestamptz | When the message was captured (SGT/UTC+8) |
| originally_from | text | Who sent the original message |
| original_chat | text | Which chat it came from |
| message | text | The message text |
| has_media | boolean | Whether the message had an attachment |
| status | text | Open / Done / Snoozed |
| notes | text | Timestamp when actioned, or snooze-until time |

---

## Troubleshooting

**Bot doesn't respond**
- Check Railway logs for startup errors — the bot will print exactly which env var is missing
- Make sure all three env vars are set in Railway

**"Log failed" error when forwarding**
- Check that your Supabase `service_role` key is set (not the `anon` key)
- Confirm the `inbox` table exists — run `schema.sql` in the Supabase SQL editor

**Snooze time isn't understood**
- Try a more explicit format: `tomorrow 9am`, `in 3 hours`, or `2026-04-15 10:00`

**Items not resurfacing after snooze**
- Snoozed items reappear the next time you run `/open` after the snooze time passes — there's no push notification

---

## License

MIT — use it, modify it, build on top of it.
