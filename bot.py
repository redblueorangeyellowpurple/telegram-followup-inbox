"""
TC Acoustic — Telegram Follow Up Inbox Bot
Compatible with python-telegram-bot v20+ and Railway deployment
Reads Google credentials from environment variable (not file)
"""

import logging
import os
import json
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GOOGLE_SHEET_ID    = os.getenv("GOOGLE_SHEET_ID", "")
INBOX_CHAT_NAME    = "Follow Up Inbox"
WORKSHEET_NAME     = "TelegramInbox"

logging.basicConfig(
    format="%(asctime)s — %(levelname)s — %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    # Try reading credentials from environment variable first (Railway)
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        creds_info = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
    else:
        # Fall back to file (local development)
        creds_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
        creds = Credentials.from_service_account_file(creds_file, scopes=scopes)

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

    chat_title = message.chat.title or ""
    is_private = message.chat.type == "private"
    is_inbox   = INBOX_CHAT_NAME.lower() in chat_title.lower()

    if not is_private and not is_inbox:
        return

    # Extract forwarded origin
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
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        worksheet = get_sheet()
        worksheet.append_row([timestamp, originally_from, original_chat, text, has_media, "Open", ""])
        logger.info(f"Logged: {originally_from} — {text[:60]}")
        await message.reply_text("✅ Captured.")
    except Exception as e:
        logger.error(f"Failed to log: {e}")
        await message.reply_text(f"⚠️ Log failed: {e}")


def main():
    logger.info("Starting Follow Up Inbox Bot...")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    logger.info("Bot running.")
    app.run_polling()


if __name__ == "__main__":
    main()

