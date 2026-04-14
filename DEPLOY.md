# Hosting Guide — Follow Up Inbox Bot (Shared/SaaS Mode)

One Railway deployment, anyone can use the bot. No setup required for end users.

---

## Step 1 — Create a Telegram bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` → follow the prompts to name it
3. Copy the token (looks like `123456:ABC-DEF...`)

> Use a **new bot** — do not reuse a bot that's already running another deployment.

---

## Step 2 — Set up Supabase

1. Go to [supabase.com](https://supabase.com) → create a new project
2. Once created → go to **SQL Editor**
3. Paste and run the contents of `schema.sql` (in this repo) — this creates the `inbox` table
4. Go to **Project Settings → API** → copy:
   - **Project URL** → this is your `SUPABASE_URL`
   - **service_role** secret key → this is your `SUPABASE_KEY` (use service_role, not anon)

---

## Step 3 — Deploy to Railway

1. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub Repo
2. Select this repo and set the branch to `supabase-saas`
3. Go to **Variables** and add:

   | Variable | Value |
   |---|---|
   | `TELEGRAM_BOT_TOKEN` | From Step 1 |
   | `SUPABASE_URL` | From Step 2 |
   | `SUPABASE_KEY` | From Step 2 |

4. Railway detects the `Procfile` automatically and starts `python bot.py`

---

## Step 4 — Verify it works

1. Open Telegram → find your bot → send `/start` → should get the welcome message
2. Forward any message to it → should reply "✅ Captured"
3. Check Supabase → Table Editor → `inbox` → confirm a row appears
4. Send `/open` → should list the item
5. Send `/done 1` → item should disappear from `/open`

---

## Step 5 — Share it

Once Step 4 passes, send people your bot's `@username`. They just message it — no setup on their end.

---

## Troubleshooting

**Bot doesn't respond**
- Check Railway logs — the bot prints exactly which env var is missing on startup

**"Log failed" when forwarding**
- Confirm you used the `service_role` key, not the `anon` key
- Confirm the `inbox` table exists — re-run `schema.sql` in the Supabase SQL editor

**Snooze time not understood**
- Try a more explicit format: `tomorrow 9am`, `in 3 hours`, `2026-04-15 10:00`

**Snoozed items not resurfacing**
- They reappear the next time you run `/open` after the snooze time passes — no push notification

---

## Railway Template Listing

*The section below is the Railway marketplace description for this template.*

---

# Deploy and Host Telegram Follow-Up Inbox Bot on Railway

A Telegram bot that turns your chat into a personal follow-up inbox. Forward messages or drop them in a group called "Follow Up Inbox" — then manage everything with simple commands like `/open`, `/done`, `/due`, and `/snooze`.

## About Hosting Telegram Follow-Up Inbox Bot

This bot runs as a single Python worker process on Railway, polling Telegram for new messages. All your data is stored in your own Supabase PostgreSQL database — Railway hosts the bot, Supabase holds the rows. There's no web server, no frontend, and no shared database. Once deployed, the bot runs continuously in the background. You interact with it entirely through Telegram. Setup takes about 10 minutes and requires a free Supabase account and a Telegram bot token from @BotFather.

## Common Use Cases

- Capturing follow-up tasks from Telegram conversations without leaving the app
- Logging forwarded messages from group chats as actionable inbox items
- Managing a personal task list with due dates and snooze reminders via Telegram

## Dependencies for Telegram Follow-Up Inbox Bot Hosting

- A Telegram Bot Token (free, from @BotFather)
- A Supabase project (free tier works) with the `inbox` table created via the provided `schema.sql`

### Deployment Dependencies

- Telegram Bot: https://t.me/BotFather
- Supabase (database + API): https://supabase.com
- Schema setup: run `schema.sql` from this repo in your Supabase SQL editor before first deploy

### Implementation Details

Set these 3 environment variables in Railway before deploying:

```
TELEGRAM_BOT_TOKEN   # from @BotFather
SUPABASE_URL         # Supabase → Project Settings → API → Project URL
SUPABASE_KEY         # Supabase → Project Settings → API → service_role secret key
```

Then run this SQL once in your Supabase SQL editor:

```sql
CREATE TABLE IF NOT EXISTS inbox (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT        NOT NULL,
    timestamp       TIMESTAMPTZ   NOT NULL,
    originally_from TEXT,
    original_chat   TEXT,
    message         TEXT,
    has_media       BOOLEAN       DEFAULT FALSE,
    status          TEXT          DEFAULT 'Open',
    notes           TEXT          DEFAULT '',
    due_date        TIMESTAMPTZ   DEFAULT NULL,
    created_at      TIMESTAMPTZ   DEFAULT NOW()
);
ALTER TABLE inbox ENABLE ROW LEVEL SECURITY;
```

## Why Deploy Telegram Follow-Up Inbox Bot on Railway?

Railway is a singular platform to deploy your infrastructure stack. Railway will host your infrastructure so you don't have to deal with configuration, while allowing you to vertically and horizontally scale it.

By deploying Telegram Follow-Up Inbox Bot on Railway, you are one step closer to supporting a complete full-stack application with minimal burden. Host your servers, databases, AI agents, and more on Railway.
