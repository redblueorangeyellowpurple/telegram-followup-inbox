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
