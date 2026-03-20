"""Handlers for /start, /help, and /settings commands."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from database import get_or_create_user, update_user_settings

logger = logging.getLogger(__name__)

WELCOME_MSG = """👋 *Welcome to CashWhisper!*

I'm your personal expense tracker. Just tell me about your spending — by voice or text — and I'll log everything for you.

💬 *Text:* Type something like:
  `spent 50k on lunch and 20k taxi`

🎙 *Voice:* Send a voice message describing your expenses.

📊 *Commands:*
  /today — Today's spending
  /week — Last 7 days
  /month — This month
  /report — Monthly AI coaching report
  /settings — Your preferences
  /help — Show this message

Let's get started! 🚀"""

HELP_MSG = """📖 *CashWhisper — Help*

*Logging expenses:*
• Send a text message: `120000 uzs groceries` or `spent 80k on food`
• Send a voice message describing your spending
• I'll auto-categorize and save everything!

*Summary commands:*
• /today — Today's total & categories
• /week — Last 7 days breakdown
• /month — Current month overview
• /report — Get an AI-powered monthly coaching report

*Settings:*
• /settings — View & update your preferences
• /currency USD — Change your base currency
• /timezone America/New_York — Change timezone
• /reminder on — Enable daily check-in
• /reminder off — Disable daily check-in
• /reminder 21:00 — Set reminder time

*Categories:*
food · transport · groceries · shopping · bills · subscriptions · entertainment · health · education · other"""


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

    reminder_status = "✅ On" if db_user["daily_reminder_enabled"] else "❌ Off"
    msg = (
        "⚙️ *Your Settings*\n\n"
        f"💱 Currency: `{db_user['currency']}`\n"
        f"🌍 Timezone: `{db_user['timezone']}`\n"
        f"⏰ Daily reminder: {reminder_status}\n"
        f"🕘 Reminder time: `{db_user['daily_reminder_time']}`\n\n"
        "*Update with:*\n"
        "`/currency USD`\n"
        "`/timezone America/New_York`\n"
        "`/reminder on` or `/reminder off`\n"
        "`/reminder 21:00`"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def currency_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /currency <CODE> — change base currency."""
    if not context.args:
        await update.message.reply_text("Usage: `/currency USD`", parse_mode="Markdown")
        return
    currency = context.args[0].upper()
    await update_user_settings(update.effective_user.id, currency=currency)
    await update.message.reply_text(f"✅ Currency set to *{currency}*", parse_mode="Markdown")


async def timezone_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /timezone <TZ> — change timezone."""
    if not context.args:
        await update.message.reply_text(
            "Usage: `/timezone Asia/Tashkent`", parse_mode="Markdown"
        )
        return
    tz = context.args[0]
    await update_user_settings(update.effective_user.id, timezone=tz)
    await update.message.reply_text(f"✅ Timezone set to *{tz}*", parse_mode="Markdown")


async def reminder_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /reminder on|off|HH:MM — configure daily check-in."""
    if not context.args:
        await update.message.reply_text(
            "Usage:\n`/reminder on` — enable\n`/reminder off` — disable\n`/reminder 21:00` — set time",
            parse_mode="Markdown",
        )
        return

    arg = context.args[0].lower()
    if arg == "on":
        await update_user_settings(update.effective_user.id, daily_reminder_enabled=True)
        await update.message.reply_text("✅ Daily reminder *enabled*!", parse_mode="Markdown")
    elif arg == "off":
        await update_user_settings(update.effective_user.id, daily_reminder_enabled=False)
        await update.message.reply_text("✅ Daily reminder *disabled*.", parse_mode="Markdown")
    elif ":" in arg:
        await update_user_settings(update.effective_user.id, daily_reminder_time=arg)
        await update.message.reply_text(
            f"✅ Reminder time set to *{arg}*", parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "❓ Use `/reminder on`, `/reminder off`, or `/reminder 21:00`",
            parse_mode="Markdown",
        )
