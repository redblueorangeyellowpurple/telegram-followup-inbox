"""
Follow Up Inbox — Telegram Bot
- Forward messages → logged to Supabase, per user
- /open → lists your open items
- /done [n] → marks item n as Done
- /snooze [n] → snooze item n until a time you specify
- /delete [n] → permanently removes item n
- /help → shows commands
"""

import logging
import os
from datetime import datetime, timezone, timedelta
import dateparser
from supabase import create_client, Client
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ConversationHandler, filters, ContextTypes

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
SUPABASE_URL       = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY       = os.getenv("SUPABASE_KEY", "")
INBOX_CHAT_NAME    = "Follow Up Inbox"
SGT                = timezone(timedelta(hours=8))

WAITING_SNOOZE_TIME = 0
WAITING_DUE_DATE    = 1

logging.basicConfig(format="%(asctime)s — %(levelname)s — %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_config():
    """Exit with a clear error if required env vars are missing."""
    errors = []
    if not TELEGRAM_BOT_TOKEN:
        errors.append("  • TELEGRAM_BOT_TOKEN is not set")
    if not SUPABASE_URL:
        errors.append("  • SUPABASE_URL is not set")
    if not SUPABASE_KEY:
        errors.append("  • SUPABASE_KEY is not set")
    if errors:
        logger.error("Bot cannot start — missing configuration:\n" + "\n".join(errors))
        raise SystemExit(1)
    logger.info("Config OK — all required env vars present.")


def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def get_open_items(user_id: int) -> list:
    """Return open items plus snoozed items past their snooze time for this user."""
    sb = get_supabase()

    open_result = (
        sb.table("inbox")
        .select("*")
        .eq("user_id", user_id)
        .eq("status", "Open")
        .order("id")
        .execute()
    )
    items = list(open_result.data)

    snoozed_result = (
        sb.table("inbox")
        .select("*")
        .eq("user_id", user_id)
        .eq("status", "Snoozed")
        .order("id")
        .execute()
    )
    now = datetime.now(SGT)
    for item in snoozed_result.data:
        notes = item.get("notes", "") or ""
        if notes.startswith("Snoozed until "):
            try:
                snooze_str   = notes[len("Snoozed until "):].replace(" SGT", "")
                snooze_until = datetime.strptime(snooze_str, "%Y-%m-%d %H:%M").replace(tzinfo=SGT)
                if now >= snooze_until:
                    items.append(item)
            except Exception:
                pass

    return items


# ── COMMAND HANDLERS ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Welcome to Follow Up Inbox!*\n\n"
        "Forward any Telegram message here and it's saved to your inbox.\n\n"
        "When you're ready to action things:\n"
        "/open — see everything waiting\n"
        "/done 2 — mark item 2 as done\n"
        "/due 2 Friday — set a due date on item 2\n"
        "/snooze 2 — hide item 2 until a time you choose\n"
        "/delete 2 — remove item 2 permanently\n\n"
        "That's it. Start forwarding.",
        parse_mode="Markdown"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *Follow Up Inbox — Commands*\n\n"
        "/open — list all open items\n"
        "/done [n] — mark item n as done\n"
        "/due [n] [date] — set a due date (e.g. /due 2 Friday)\n"
        "/snooze [n] — snooze item n (you'll be asked until when)\n"
        "/delete [n] — permanently remove item n\n"
        "/help — show this menu\n\n"
        "To capture: just forward any message here.",
        parse_mode="Markdown"
    )


async def cmd_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        items = get_open_items(user_id)

        if not items:
            await update.message.reply_text("✅ All clear — no open items!")
            return

        lines = ["📋 *Open Items:*\n"]
        for idx, item in enumerate(items, start=1):
            timestamp = item.get("timestamp", "")
            sender    = item.get("originally_from", "")
            message   = item.get("message", "")
            preview   = message[:80] + "..." if len(message) > 80 else message
            try:
                ts   = datetime.fromisoformat(timestamp).astimezone(SGT)
                age  = datetime.now(SGT) - ts
                flag = "🔴 " if age.days >= 1 else "🟠 " if age.seconds > 3600 * 4 else ""
            except Exception:
                flag = ""
            ts_display = timestamp[:16] if timestamp else ""
            due_raw  = item.get("due_date") or ""
            due_part = ""
            if due_raw:
                try:
                    due_dt = datetime.fromisoformat(due_raw).astimezone(SGT)
                    if due_dt < datetime.now(SGT):
                        due_part = f" · _⚠️ Due {due_dt.strftime('%b %-d')} (overdue)_"
                    else:
                        due_part = f" · _📆 Due {due_dt.strftime('%b %-d')}_"
                except Exception:
                    pass
            lines.append(f"{flag}*{idx}.* {preview}\n   _From: {sender}_\n   _📅 {ts_display}_{due_part}\n")

        lines.append("\nReply /done [n], /due [n], /snooze [n], or /delete [n]")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    except Exception as e:
        logger.error(f"cmd_open error: {e}")
        await update.message.reply_text(f"⚠️ Error fetching items: {e}")


async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        if not context.args:
            await update.message.reply_text("Usage: /done [number] — e.g. /done 2")
            return

        n     = int(context.args[0])
        items = get_open_items(user_id)

        if n < 1 or n > len(items):
            await update.message.reply_text(f"⚠️ No item {n}. Use /open to see current list.")
            return

        item      = items[n - 1]
        done_time = datetime.now(SGT).strftime("%Y-%m-%d %H:%M SGT")

        get_supabase().table("inbox").update({
            "status": "Done",
            "notes":  f"Marked done {done_time}"
        }).eq("id", item["id"]).execute()

        await update.message.reply_text(
            f"✅ Done: _{item['message'][:60]}_",
            parse_mode="Markdown"
        )
        logger.info(f"Marked item {item['id']} as Done")

    except ValueError:
        await update.message.reply_text("Usage: /done [number] — e.g. /done 2")
    except Exception as e:
        logger.error(f"cmd_done error: {e}")
        await update.message.reply_text(f"⚠️ Error: {e}")


async def cmd_snooze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Usage: /snooze [number] — e.g. /snooze 2")
        return ConversationHandler.END

    try:
        n = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Usage: /snooze [number] — e.g. /snooze 2")
        return ConversationHandler.END

    try:
        items = get_open_items(user_id)

        if n < 1 or n > len(items):
            await update.message.reply_text(f"⚠️ No item {n}. Use /open to see current list.")
            return ConversationHandler.END

        item = items[n - 1]
        context.user_data["snooze_id"]      = item["id"]
        context.user_data["snooze_preview"] = item["message"][:60]

        await update.message.reply_text(
            f"⏸ Snooze: _{item['message'][:60]}_\n\nUntil when? (e.g. _tomorrow 9am_, _3h_, _Monday_)",
            parse_mode="Markdown"
        )
        return WAITING_SNOOZE_TIME

    except Exception as e:
        logger.error(f"cmd_snooze error: {e}")
        await update.message.reply_text(f"⚠️ Error: {e}")
        return ConversationHandler.END


async def receive_snooze_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time_text       = update.message.text.strip()
    item_id         = context.user_data.get("snooze_id")
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
        get_supabase().table("inbox").update({
            "status": "Snoozed",
            "notes":  f"Snoozed until {snooze_str}"
        }).eq("id", item_id).execute()

        await update.message.reply_text(
            f"⏸ Snoozed until {snooze_str}: _{message_preview}_",
            parse_mode="Markdown"
        )
        logger.info(f"Snoozed item {item_id} until {snooze_str}")
    except Exception as e:
        logger.error(f"receive_snooze_time error: {e}")
        await update.message.reply_text(f"⚠️ Error: {e}")

    context.user_data.clear()
    return ConversationHandler.END


async def cmd_due(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point: /due N [date] — sets a due date inline or asks if no date given."""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Usage: /due [number] [date] — e.g. /due 2 Friday or /due 2")
        return ConversationHandler.END

    try:
        n = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Usage: /due [number] [date] — e.g. /due 2 Friday or /due 2")
        return ConversationHandler.END

    try:
        items = get_open_items(user_id)

        if n < 1 or n > len(items):
            await update.message.reply_text(f"⚠️ No item {n}. Use /open to see current list.")
            return ConversationHandler.END

        item            = items[n - 1]
        message_preview = item["message"][:60]

        # Inline date provided — parse and set immediately
        if len(context.args) > 1:
            date_str = " ".join(context.args[1:])
            due_dt   = dateparser.parse(
                date_str,
                settings={"PREFER_DATES_FROM": "future", "TIMEZONE": "Asia/Singapore", "RETURN_AS_TIMEZONE_AWARE": True}
            )
            if not due_dt:
                await update.message.reply_text(
                    "⚠️ Couldn't understand that date. Try _Friday_, _Apr 15_, or _tomorrow 5pm_.",
                    parse_mode="Markdown"
                )
                return ConversationHandler.END

            get_supabase().table("inbox").update({
                "due_date": due_dt.isoformat()
            }).eq("id", item["id"]).execute()
            await update.message.reply_text(
                f"📆 Due {due_dt.strftime('%b %-d')} set for: _{message_preview}_",
                parse_mode="Markdown"
            )
            logger.info(f"Set due date on item {item['id']}")
            return ConversationHandler.END

        # No date provided — ask
        context.user_data["due_id"]      = item["id"]
        context.user_data["due_preview"] = message_preview
        await update.message.reply_text(
            f"📆 Set due date for: _{message_preview}_\n\nWhen is this due? (e.g. _Friday_, _Apr 15_, _tomorrow 5pm_)",
            parse_mode="Markdown"
        )
        return WAITING_DUE_DATE

    except Exception as e:
        logger.error(f"cmd_due error: {e}")
        await update.message.reply_text(f"⚠️ Error: {e}")
        return ConversationHandler.END


async def receive_due_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives the due date from the user and writes it to Supabase."""
    time_text       = update.message.text.strip()
    item_id         = context.user_data.get("due_id")
    message_preview = context.user_data.get("due_preview", "")

    due_dt = dateparser.parse(
        time_text,
        settings={"PREFER_DATES_FROM": "future", "TIMEZONE": "Asia/Singapore", "RETURN_AS_TIMEZONE_AWARE": True}
    )

    if not due_dt:
        await update.message.reply_text(
            "⚠️ Couldn't understand that. Try _Friday_, _Apr 15_, or _tomorrow 5pm_.",
            parse_mode="Markdown"
        )
        return WAITING_DUE_DATE

    try:
        get_supabase().table("inbox").update({
            "due_date": due_dt.isoformat()
        }).eq("id", item_id).execute()
        await update.message.reply_text(
            f"📆 Due {due_dt.strftime('%b %-d')} set for: _{message_preview}_",
            parse_mode="Markdown"
        )
        logger.info(f"Set due date on item {item_id}")
    except Exception as e:
        logger.error(f"receive_due_date error: {e}")
        await update.message.reply_text(f"⚠️ Error: {e}")

    context.user_data.clear()
    return ConversationHandler.END


async def cmd_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        if not context.args:
            await update.message.reply_text("Usage: /delete [number] — e.g. /delete 2")
            return

        n     = int(context.args[0])
        items = get_open_items(user_id)

        if n < 1 or n > len(items):
            await update.message.reply_text(f"⚠️ No item {n}. Use /open to see current list.")
            return

        item = items[n - 1]
        get_supabase().table("inbox").delete().eq("id", item["id"]).execute()

        await update.message.reply_text(
            f"🗑 Deleted: _{item['message'][:60]}_",
            parse_mode="Markdown"
        )
        logger.info(f"Deleted item {item['id']}")

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
        original_chat   = "Direct note"

    text      = message.text or message.caption or "[media only]"
    has_media = bool(message.photo or message.video or message.document or message.voice or message.audio)
    timestamp = datetime.now(SGT).isoformat()
    user_id   = update.effective_user.id

    try:
        get_supabase().table("inbox").insert({
            "user_id":         user_id,
            "timestamp":       timestamp,
            "originally_from": originally_from,
            "original_chat":   original_chat,
            "message":         text,
            "has_media":       has_media,
            "status":          "Open",
            "notes":           ""
        }).execute()
        logger.info(f"Logged for user {user_id}: {originally_from} — {text[:60]}")
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

    due_conv = ConversationHandler(
        entry_points=[CommandHandler("due", cmd_due)],
        states={
            WAITING_DUE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_due_date)],
        },
        fallbacks=[],
    )

    app.add_handler(snooze_conv)
    app.add_handler(due_conv)
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("help",   cmd_help))
    app.add_handler(CommandHandler("open",   cmd_open))
    app.add_handler(CommandHandler("done",   cmd_done))
    app.add_handler(CommandHandler("delete", cmd_delete))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    logger.info("Bot running.")
    app.run_polling()

if __name__ == "__main__":
    main()
