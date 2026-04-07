"""
TC Acoustic — Telegram Follow Up Inbox Bot
- Forward messages → logs to Google Sheets
- /open → lists all open items
- /done [n] → marks item n as Done
- /snooze [n] → marks item n as Snoozed
- /help → shows commands
"""

import logging
import os
import json
from datetime import datetime, timezone, timedelta
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GOOGLE_SHEET_ID    = os.getenv("GOOGLE_SHEET_ID", "")
INBOX_CHAT_NAME    = "Follow Up Inbox"
WORKSHEET_NAME     = "TelegramInbox"
SGT                = timezone(timedelta(hours=8))

logging.basicConfig(format="%(asctime)s — %(levelname)s — %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Column indices (1-based for gspread)
COL_TIMESTAMP     = 1
COL_FROM          = 2
COL_CHAT          = 3
COL_MESSAGE       = 4
COL_MEDIA         = 5
COL_STATUS        = 6
COL_NOTES         = 7


def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=scopes)
    else:
        creds = Credentials.from_service_account_file(
            os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"), scopes=scopes
        )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(GOOGLE_SHEET_ID)

    try:
        worksheet = sheet.worksheet(WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        worksheet = sheet.add_worksheet(title=WORKSHEET_NAME, rows=5000, cols=7)
        worksheet.append_row([
            "Timestamp (SGT)", "Originally From", "Original Chat",
            "Message", "Has Media", "Status", "Notes"
        ])
    return worksheet


def get_open_items(worksheet):
    """Return list of (row_index, row_data) for all Open rows, skipping header."""
    all_rows = worksheet.get_all_values()
    open_items = []
    for i, row in enumerate(all_rows[1:], start=2):  # start=2 because row 1 is header
        if len(row) >= 6 and row[COL_STATUS - 1].strip() == "Open":
            open_items.append((i, row))
    return open_items


# ── COMMAND HANDLERS ──────────────────────────────────────────────────────────

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *Follow Up Inbox — Commands*\n\n"
        "/open — list all open items\n"
        "/done [n] — mark item n as done\n"
        "/snooze [n] — snooze item n\n"
        "/help — show this menu\n\n"
        "To capture: just forward any message here.",
        parse_mode="Markdown"
    )


async def cmd_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all open items."""
    try:
        worksheet = get_sheet()
        open_items = get_open_items(worksheet)

        if not open_items:
            await update.message.reply_text("✅ All clear — no open items!")
            return

        lines = ["📋 *Open Items:*\n"]
        for idx, (row_num, row) in enumerate(open_items, start=1):
            timestamp = row[COL_TIMESTAMP - 1]
            sender    = row[COL_FROM - 1]
            message   = row[COL_MESSAGE - 1]
            # Truncate long messages
            preview = message[:80] + "..." if len(message) > 80 else message
            # Flag overdue (more than 1 day old)
            try:
                ts = datetime.strptime(timestamp[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=SGT)
                age = datetime.now(SGT) - ts
                flag = "🔴 " if age.days >= 1 else "🟠 " if age.seconds > 3600 * 4 else ""
            except:
                flag = ""
            lines.append(f"{flag}*{idx}.* {preview}\n   _From: {sender}_\n   _📅 {timestamp[:16]}_\n")

        lines.append("\nReply /done [n] or /snooze [n]")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    except Exception as e:
        logger.error(f"cmd_open error: {e}")
        await update.message.reply_text(f"⚠️ Error fetching items: {e}")


async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mark item n as Done."""
    try:
        if not context.args:
            await update.message.reply_text("Usage: /done [number] — e.g. /done 2")
            return

        n = int(context.args[0])
        worksheet = get_sheet()
        open_items = get_open_items(worksheet)

        if n < 1 or n > len(open_items):
            await update.message.reply_text(f"⚠️ No item {n}. Use /open to see current list.")
            return

        row_num, row = open_items[n - 1]
        message_preview = row[COL_MESSAGE - 1][:60]
        done_time = datetime.now(SGT).strftime("%Y-%m-%d %H:%M SGT")

        worksheet.update_cell(row_num, COL_STATUS, "Done")
        worksheet.update_cell(row_num, COL_NOTES, f"Marked done {done_time}")

        await update.message.reply_text(
            f"✅ Done: _{message_preview}_",
            parse_mode="Markdown"
        )
        logger.info(f"Marked row {row_num} as Done")

    except ValueError:
        await update.message.reply_text("Usage: /done [number] — e.g. /done 2")
    except Exception as e:
        logger.error(f"cmd_done error: {e}")
        await update.message.reply_text(f"⚠️ Error: {e}")


async def cmd_snooze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Snooze item n — keeps it open but notes it."""
    try:
        if not context.args:
            await update.message.reply_text("Usage: /snooze [number] — e.g. /snooze 2")
            return

        n = int(context.args[0])
        worksheet = get_sheet()
        open_items = get_open_items(worksheet)

        if n < 1 or n > len(open_items):
            await update.message.reply_text(f"⚠️ No item {n}. Use /open to see current list.")
            return

        row_num, row = open_items[n - 1]
        message_preview = row[COL_MESSAGE - 1][:60]
        snooze_time = datetime.now(SGT).strftime("%Y-%m-%d %H:%M SGT")

        worksheet.update_cell(row_num, COL_STATUS, "Snoozed")
        worksheet.update_cell(row_num, COL_NOTES, f"Snoozed {snooze_time}")

        await update.message.reply_text(
            f"⏸ Snoozed: _{message_preview}_\nIt'll stay in the sheet but won't show in /open.",
            parse_mode="Markdown"
        )
        logger.info(f"Marked row {row_num} as Snoozed")

    except ValueError:
        await update.message.reply_text("Usage: /snooze [number] — e.g. /snooze 2")
    except Exception as e:
        logger.error(f"cmd_snooze error: {e}")
        await update.message.reply_text(f"⚠️ Error: {e}")


# ── MESSAGE HANDLER ───────────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    chat_title = message.chat.title or ""
    is_private = message.chat.type == "private"
    is_inbox   = INBOX_CHAT_NAME.lower() in chat_title.lower()

    if not is_private and not is_inbox:
        return

    if message.forward_origin:
        origin = message.forward_origin
        if hasattr(origin, "sender_user") and origin.sender_user:
            u = origin.sender_user
            originally_from = f"{u.first_name or ''} {u.last_name or ''}".strip()
            if u.username:
                originally_from += f" (@{u.username})"
        elif hasattr(origin, "sender_user_name"):
            originally_from = origin.sender_user_name
        elif hasattr(origin, "chat") and origin.chat:
            originally_from = origin.chat.title or "Channel"
        else:
            originally_from = "Unknown"
        original_chat = getattr(getattr(origin, "chat", None), "title", None) or "DM"
    else:
        sender = message.from_user
        originally_from = f"{sender.first_name or ''} {sender.last_name or ''}".strip() if sender else "You"
        original_chat = "Direct note"

    text      = message.text or message.caption or "[media only]"
    has_media = "Yes" if (message.photo or message.video or message.document or message.voice or message.audio) else "No"
    timestamp = datetime.now(SGT).strftime("%Y-%m-%d %H:%M:%S SGT")

    try:
        worksheet = get_sheet()
        worksheet.append_row([timestamp, originally_from, original_chat, text, has_media, "Open", ""])
        logger.info(f"Logged [{timestamp}]: {originally_from} — {text[:60]}")
        await message.reply_text("✅ Captured. Use /open to see all open items.")
    except Exception as e:
        logger.error(f"Failed to log: {e}")
        await message.reply_text(f"⚠️ Log failed: {e}")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    logger.info("Starting Follow Up Inbox Bot...")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("help",   cmd_help))
    app.add_handler(CommandHandler("open",   cmd_open))
    app.add_handler(CommandHandler("done",   cmd_done))
    app.add_handler(CommandHandler("snooze", cmd_snooze))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    logger.info("Bot running with /open, /done, /snooze commands.")
    app.run_polling()

if __name__ == "__main__":
    main()
