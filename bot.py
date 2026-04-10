"""
TC Acoustic — Telegram Follow Up Inbox Bot
- Forward messages → logs to Google Sheets
- /open → lists all open items
- /done [n] → marks item n as Done
- /snooze [n] → snooze item n until a time you specify
- /delete [n] → permanently removes item n from the sheet
- /help → shows commands
"""

import logging
import os
import json
from datetime import datetime, timezone, timedelta
import dateparser
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ConversationHandler, filters, ContextTypes

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GOOGLE_SHEET_ID    = os.getenv("GOOGLE_SHEET_ID", "")
INBOX_CHAT_NAME    = "Follow Up Inbox"
WORKSHEET_NAME     = "TelegramInbox"
SGT                = timezone(timedelta(hours=8))

WAITING_SNOOZE_TIME = 0

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


def validate_config():
    """Check required env vars are present and credentials are loadable. Exit with a clear message if not."""
    errors = []

    if not TELEGRAM_BOT_TOKEN:
        errors.append("  • TELEGRAM_BOT_TOKEN is not set")
    if not GOOGLE_SHEET_ID:
        errors.append("  • GOOGLE_SHEET_ID is not set")

    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    creds_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    if not creds_json and not os.path.exists(creds_file):
        errors.append(
            f"  • No Google credentials found. Set GOOGLE_CREDENTIALS_JSON or place credentials.json at '{creds_file}'"
        )
    elif creds_json:
        try:
            json.loads(creds_json)
        except json.JSONDecodeError:
            errors.append("  • GOOGLE_CREDENTIALS_JSON is not valid JSON")

    if errors:
        logger.error("Bot cannot start — missing configuration:\n" + "\n".join(errors))
        logger.error("See the README for setup instructions.")
        raise SystemExit(1)

    logger.info("Config OK — all required env vars present.")


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
    """Return list of (row_index, row_data) for Open rows, plus Snoozed rows past their snooze time."""
    all_rows = worksheet.get_all_values()
    now = datetime.now(SGT)
    open_items = []
    for i, row in enumerate(all_rows[1:], start=2):  # start=2 because row 1 is header
        if len(row) < 6:
            continue
        status = row[COL_STATUS - 1].strip()
        if status == "Open":
            open_items.append((i, row))
        elif status == "Snoozed" and len(row) >= 7:
            notes = row[COL_NOTES - 1]
            if notes.startswith("Snoozed until "):
                try:
                    snooze_str = notes[len("Snoozed until "):].replace(" SGT", "")
                    snooze_until = datetime.strptime(snooze_str, "%Y-%m-%d %H:%M").replace(tzinfo=SGT)
                    if now >= snooze_until:
                        open_items.append((i, row))
                except Exception:
                    pass
    return open_items


# ── COMMAND HANDLERS ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Welcome to Follow Up Inbox!*\n\n"
        "This bot logs messages from Telegram into a Google Sheet so nothing slips through.\n\n"
        "*Quick setup (5 steps):*\n\n"
        "1️⃣ *Telegram bot* — create yours at @BotFather with /newbot. Copy the token into your `TELEGRAM_BOT_TOKEN` env var.\n\n"
        "2️⃣ *Google Sheet* — create a new sheet, copy its ID from the URL "
        "(`docs.google.com/spreadsheets/d/*YOUR_ID*/edit`). Set it as `GOOGLE_SHEET_ID`.\n\n"
        "3️⃣ *Google credentials* — in Google Cloud Console, create a project → enable the Sheets API → "
        "create a Service Account → download the JSON key. Set its contents as `GOOGLE_CREDENTIALS_JSON`.\n\n"
        "4️⃣ *Share your sheet* — open the sheet and share it (Editor access) with the service account email "
        "from the JSON (`client_email` field).\n\n"
        "5️⃣ *Deploy* — push to Railway (or run locally with `python bot.py`). "
        "Set the three env vars above in your deployment settings.\n\n"
        "Once running, forward any Telegram message here and it'll be captured.\n\n"
        "Type /help to see all commands.",
        parse_mode="Markdown"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *Follow Up Inbox — Commands*\n\n"
        "/open — list all open items\n"
        "/done [n] — mark item n as done\n"
        "/snooze [n] — snooze item n (you'll be asked until when)\n"
        "/delete [n] — permanently remove item n\n"
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

        lines.append("\nReply /done [n], /snooze [n], or /delete [n]")
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
    """Entry point: /snooze N — asks the user until when."""
    if not context.args:
        await update.message.reply_text("Usage: /snooze [number] — e.g. /snooze 2")
        return ConversationHandler.END

    try:
        n = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Usage: /snooze [number] — e.g. /snooze 2")
        return ConversationHandler.END

    try:
        worksheet = get_sheet()
        open_items = get_open_items(worksheet)

        if n < 1 or n > len(open_items):
            await update.message.reply_text(f"⚠️ No item {n}. Use /open to see current list.")
            return ConversationHandler.END

        row_num, row = open_items[n - 1]
        message_preview = row[COL_MESSAGE - 1][:60]
        context.user_data["snooze_row"] = row_num
        context.user_data["snooze_preview"] = message_preview

        await update.message.reply_text(
            f"⏸ Snooze: _{message_preview}_\n\nUntil when? (e.g. _tomorrow 9am_, _3h_, _Monday_)",
            parse_mode="Markdown"
        )
        return WAITING_SNOOZE_TIME

    except Exception as e:
        logger.error(f"cmd_snooze error: {e}")
        await update.message.reply_text(f"⚠️ Error: {e}")
        return ConversationHandler.END


async def receive_snooze_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives the snooze-until time from the user and writes it to the sheet."""
    time_text = update.message.text.strip()
    row_num = context.user_data.get("snooze_row")
    message_preview = context.user_data.get("snooze_preview", "")

    snooze_until = dateparser.parse(
        time_text,
        settings={"PREFER_DATES_FROM": "future", "TIMEZONE": "Asia/Singapore", "RETURN_AS_TIMEZONE_AWARE": True}
    )

    if not snooze_until:
        await update.message.reply_text(
            "⚠️ Couldn't understand that. Try _tomorrow 9am_, _3h_, or _Monday 10am_.",
            parse_mode="Markdown"
        )
        return WAITING_SNOOZE_TIME

    snooze_str = snooze_until.strftime("%Y-%m-%d %H:%M SGT")

    try:
        worksheet = get_sheet()
        worksheet.update_cell(row_num, COL_STATUS, "Snoozed")
        worksheet.update_cell(row_num, COL_NOTES, f"Snoozed until {snooze_str}")

        await update.message.reply_text(
            f"⏸ Snoozed until {snooze_str}: _{message_preview}_",
            parse_mode="Markdown"
        )
        logger.info(f"Snoozed row {row_num} until {snooze_str}")
    except Exception as e:
        logger.error(f"receive_snooze_time error: {e}")
        await update.message.reply_text(f"⚠️ Error: {e}")

    context.user_data.clear()
    return ConversationHandler.END


async def cmd_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Permanently delete item n from the sheet."""
    try:
        if not context.args:
            await update.message.reply_text("Usage: /delete [number] — e.g. /delete 2")
            return

        n = int(context.args[0])
        worksheet = get_sheet()
        open_items = get_open_items(worksheet)

        if n < 1 or n > len(open_items):
            await update.message.reply_text(f"⚠️ No item {n}. Use /open to see current list.")
            return

        row_num, row = open_items[n - 1]
        message_preview = row[COL_MESSAGE - 1][:60]

        worksheet.delete_rows(row_num)

        await update.message.reply_text(
            f"🗑 Deleted: _{message_preview}_",
            parse_mode="Markdown"
        )
        logger.info(f"Deleted row {row_num}")

    except ValueError:
        await update.message.reply_text("Usage: /delete [number] — e.g. /delete 2")
    except Exception as e:
        logger.error(f"cmd_delete error: {e}")
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
    validate_config()
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    snooze_conv = ConversationHandler(
        entry_points=[CommandHandler("snooze", cmd_snooze)],
        states={
            WAITING_SNOOZE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_snooze_time)],
        },
        fallbacks=[],
    )

    app.add_handler(snooze_conv)
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("help",   cmd_help))
    app.add_handler(CommandHandler("open",   cmd_open))
    app.add_handler(CommandHandler("done",   cmd_done))
    app.add_handler(CommandHandler("delete", cmd_delete))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    logger.info("Bot running with /open, /done, /snooze, /delete commands.")
    app.run_polling()

if __name__ == "__main__":
    main()
