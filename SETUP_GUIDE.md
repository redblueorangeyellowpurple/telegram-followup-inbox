# TC Acoustic — Telegram Logger Setup Guide
# Complete step-by-step. No prior technical experience required.

---

## WHAT YOU'RE BUILDING

A silent Telegram bot that sits in your chats and logs every message to a
Google Sheet. Claude reads that sheet as part of your daily brief — surfacing
todos, open loops, and delegated items from Telegram the same way it does
from Gmail and Granola.

Estimated setup time: ~30 minutes.

---

## STAGE 1 — Create your Telegram bot (5 min)

1. Open Telegram and search for **@BotFather**
2. Start a chat and type: /newbot
3. BotFather will ask for a name → type: TC Brief Bot
4. BotFather will ask for a username → type: tcacoustic_brief_bot
   (if taken, try: tcbrief_fanny_bot or similar — must end in "bot")
5. BotFather gives you a TOKEN. It looks like:
   1234567890:ABCDefGhIJKlmNoPQRsTUVwxyZ
   → SAVE THIS. You'll need it in Stage 3.

6. One more step — disable privacy mode so the bot can read group messages:
   In BotFather, type: /setprivacy
   Select your bot → choose: Disable
   This allows the bot to see all messages in groups.

---

## STAGE 2 — Set up Google Sheets (5 min)

1. Go to Google Sheets: https://sheets.google.com
2. Create a new spreadsheet
3. Name it: TC Acoustic — Telegram Log
4. Copy the Sheet ID from the URL:
   https://docs.google.com/spreadsheets/d/THIS_IS_YOUR_SHEET_ID/edit
   → SAVE THIS.

---

## STAGE 3 — Connect Google Sheets to the bot (10 min)

This lets the bot write to your sheet automatically.

1. Go to: https://console.cloud.google.com
2. Create a new project → name it: TC Telegram Bot
3. In the search bar, search for "Google Sheets API" → Enable it
4. Also search for "Google Drive API" → Enable it
5. Go to: IAM & Admin → Service Accounts → Create Service Account
   Name: telegram-logger
   Click Create and Continue → Done
6. Click on the service account you just created
7. Go to Keys tab → Add Key → Create new key → JSON
   A credentials.json file downloads to your computer.
   → KEEP THIS FILE SAFE. Treat it like a password.
8. Open your Google Sheet
   Share it with the service account email (looks like:
   telegram-logger@tc-telegram-bot.iam.gserviceaccount.com)
   Give it Editor access.

---

## STAGE 4 — Deploy the bot (10 min)

You have two options:

### Option A — Run on your computer (simplest, but requires laptop to be on)

1. Make sure Python is installed: https://www.python.org/downloads/
2. Open Terminal (Mac) or Command Prompt (Windows)
3. Run:
   pip install python-telegram-bot gspread google-auth
4. Put these three files in the same folder:
   - bot.py (provided)
   - credentials.json (downloaded in Stage 3)
5. Set your credentials:
   On Mac/Linux, run in Terminal:
     export TELEGRAM_BOT_TOKEN="your_token_here"
     export GOOGLE_SHEET_ID="your_sheet_id_here"
   On Windows, run in Command Prompt:
     set TELEGRAM_BOT_TOKEN=your_token_here
     set GOOGLE_SHEET_ID=your_sheet_id_here
6. Run the bot:
   python bot.py
7. You should see: "Bot is running."

### Option B — Run in the cloud (recommended — always on, no laptop needed)

Use Railway.app — free tier is enough for this bot.

1. Go to: https://railway.app — sign up with GitHub
2. Click New Project → Deploy from GitHub repo
   (Upload the bot.py and credentials.json files to a private GitHub repo first)
3. Add environment variables in Railway settings:
   TELEGRAM_BOT_TOKEN = your_token
   GOOGLE_SHEET_ID = your_sheet_id
   GOOGLE_CREDENTIALS_FILE = credentials.json
4. Deploy. Railway keeps it running 24/7.

---

## STAGE 5 — Add the bot to your chats

1. Open each Telegram group you want monitored
2. Tap the group name → Add Members
3. Search for your bot username (e.g. @tcacoustic_brief_bot)
4. Add it. It will join silently.

For DMs: The bot can only log DMs if you message IT directly, or if you
forward messages to it. DM monitoring of other people's chats is not
possible via Telegram's API — this is a Telegram privacy restriction.

To capture your own DMs: Start a chat with your bot and forward important
messages to it. It will log them automatically.

---

## STAGE 6 — Verify it's working

1. Send a message in any group where the bot was added
2. Open your Google Sheet
3. You should see a new row appear within seconds:
   Timestamp | Chat Type | Chat Name | Sender | Message | ...

If no rows appear:
- Check that privacy mode is disabled (Stage 1, Step 6)
- Confirm the bot was added to the group as a member
- Check the bot is running (Terminal should show log lines)

---

## WHAT CLAUDE WILL SWEEP

Once running, Claude reads your Telegram Log sheet as part of the daily brief and extracts:

✅ Todos and tasks mentioned in chats
✅ Questions asked but not answered (open loops)
✅ Items delegated to your team (Gerry, Sasha, May, Sihui, Michelle, Min, Mo, Daryl, Bryan etc.)
✅ Decisions made or pending
✅ Urgent or time-sensitive messages

The sheet acts as Claude's window into Telegram — same logic as Gmail, different source.

---

## QUESTIONS?

Tell Claude: "Help me with the Telegram bot setup" at any stage
and paste the error message or where you're stuck.
