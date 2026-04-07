"""
TC Acoustic — Telegram Follow Up Inbox Bot
Compatible with python-telegram-bot v21+
"""

import logging
import os
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
GOOGLE_SHEET_ID    = os.getenv("GOOGLE_SHEET_ID", "YOUR_SHEET_ID_HERE")
CREDENTIALS_FILE   = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
INBOX_CHAT_NAME    = "Follow Up Inbox"
WORKSHEET_NAME     = "TelegramInbox"

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(GOOGLE_SHEET_ID)

    try:
        worksheet = sheet.worksheet(WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        worksheet = sheet.add_worksheet(title=WORKSHEET_NAME, rows=5000, cols=7)
        worksheet.append_row([
            "Timestamp (SGT)",
            "Originally From",
            "Original Chat",
            "Message",
            "Has Media",
            "Status",
            "Notes"
        ])
        logger.info(f"Created worksheet: {WORKSHEET_NAME}")

    return worksheet


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Only process the inbox chat or direct DMs to the bot
    chat_title = message.chat.title or ""
    if message.chat.type != "private" and INBOX_CHAT_NAME.lower() not in chat_title.lower():
        return

    # Extract forwarded origin
    if message.forward_origin:
        origin = message.forward_origin
        origin_type = type(origin).__name__

        if hasattr(origin, 'sender_user') and origin.sender_user:
            u = origin.sender_user
            originally_from = f"{u.first_name or ''} {u.last_name or ''}".strip()
            if u.username:
                originally_from += f" (@{u.username})"
        elif hasattr(origin, 'sender_user_name'):
            originally_from = getattr(origin, 'sender_user_name', 'Hidden user')
        elif hasattr(origin, 'chat') and origin.chat:
            originally_from = getattr(origin.chat, 'title', 'Channel')
        else:
            originally_from = "Unknown"

        original_chat = "DM"
        if hasattr(origin, 'chat') and origin.chat:
            original_chat = getattr(origin.chat, 'title', 'DM')
    else:
        sender = message.from_user
        if sender:
            originally_from = f"{sender.first_name or ''} {sender.last_name or ''}".strip()
        else:
            originally_from = "You"
        original_chat = "Direct note"

    text = message.text or message.caption or "[media only]"
    has_media = "Yes" if (
        message.photo or message.video or message.document
        or message.voice or message.audio
    ) else "No"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        worksheet = get_sheet()
        worksheet.append_row([
            timestamp,
            originally_from,
            original_chat,
            text,
            has_media,
            "Open",
            ""
        ])
        logger.info(f"Logged: {originally_from} — {text[:60]}")
        await message.reply_text("✅ Captured.")
    except Exception as e:
        logger.error(f"Failed to log: {e}")
        await message.reply_text(f"⚠️ Log failed: {str(e)[:100]}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Follow Up Inbox Bot is running.\n\n"
        "Forward any Telegram message here and I'll log it for your daily brief."
    )


def main():
    logger.info("Starting Follow Up Inbox Bot...")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    from telegram.ext import CommandHandler
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    logger.info("Bot running. Forward messages to your Follow Up Inbox.")
    app.run_polling()


if __name__ == "__main__":
    main()
