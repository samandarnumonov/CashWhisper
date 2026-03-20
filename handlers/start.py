"""Handlers for /start, /help, and /settings commands."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from database import get_or_create_user, update_user_settings

logger = logging.getLogger(__name__)

WELCOME_MSG = """hello. i am cashwhisper.

tell me what you spent (voice or text), and i'll save it.

· "spent 50k lunch"
· "20k taxi"

commands:
/today  · today's spending
/week   · last 7 days
/month  · this month
/report · ai monthly summary
/help   · all commands
/options · settings

let's begin."""

HELP_MSG = """help

log expenses:
· text: "120000 uzs groceries" or "50k coffee"
· voice: describe your spending

summaries:
/today  · today
/week   · last 7 days
/month  · this month
/report · ai summary

settings:
/options · view settings
/currency USD · change currency
/timezone America/New_York · change timezone
/reminder on/off · toggle daily check-in
/reminder 21:00 · set time

categories:
food, transport, groceries, shopping, bills, subscriptions, entertainment, health, education, other"""



async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — welcome the user and register them."""
    user = update.effective_user
    await get_or_create_user(
        telegram_user_id=user.id,
        username=user.username,
        first_name=user.first_name,
    )
    await update.message.reply_text(WELCOME_MSG, parse_mode="Markdown")
    logger.info("New user registered: %s (%s)", user.first_name, user.id)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help — show usage instructions."""
    await update.message.reply_text(HELP_MSG, parse_mode="Markdown")


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /settings — show current settings."""
    user = update.effective_user
    db_user = await get_or_create_user(telegram_user_id=user.id)

    reminder_status = "on" if db_user["daily_reminder_enabled"] else "off"
    msg = (
        "settings\n\n"
        f"currency · {db_user['currency']}\n"
        f"timezone · {db_user['timezone']}\n"
        f"reminder · {reminder_status} at {db_user['daily_reminder_time']}\n"
    )
    await update.message.reply_text(msg)



async def currency_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /currency <CODE> — change base currency."""
    if not context.args:
        await update.message.reply_text("usage: /currency USD")
        return
    currency = context.args[0].upper()
    await update_user_settings(update.effective_user.id, currency=currency)
    await update.message.reply_text(f"currency set to {currency}")

async def timezone_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /timezone <TZ> — change timezone."""
    if not context.args:
        await update.message.reply_text("usage: /timezone Asia/Tashkent")
        return
    tz = context.args[0]
    await update_user_settings(update.effective_user.id, timezone=tz)
    await update.message.reply_text(f"timezone set to {tz}")



async def reminder_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /reminder on|off|HH:MM — configure daily check-in."""
    if not context.args:
        await update.message.reply_text("usage: /reminder on|off|21:00")
        return

    arg = context.args[0].lower()
    if arg == "on":
        await update_user_settings(update.effective_user.id, daily_reminder_enabled=True)
        await update.message.reply_text("daily reminder on")
    elif arg == "off":
        await update_user_settings(update.effective_user.id, daily_reminder_enabled=False)
        await update.message.reply_text("daily reminder off")
    elif ":" in arg:
        await update_user_settings(update.effective_user.id, daily_reminder_time=arg)
        await update.message.reply_text(f"reminder time set to {arg}")
    else:
        await update.message.reply_text("usage: /reminder on|off|21:00")

