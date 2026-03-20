"""Handlers for /today, /week, /month, and /report commands."""

import logging
from datetime import date, timedelta
from telegram import Update
from telegram.ext import ContextTypes

from database import get_or_create_user, get_expenses_by_range, get_monthly_summary
from services.reporter import generate_monthly_report

logger = logging.getLogger(__name__)


def _category_emoji(category: str) -> str:
    emojis = {
        "food": "🍽",
        "transport": "🚕",
        "groceries": "🛒",
        "shopping": "🛍",
        "bills": "🧾",
        "subscriptions": "📱",
        "entertainment": "🎬",
        "health": "💊",
        "education": "📚",
        "other": "📌",
    }
    return emojis.get(category, "📌")


def _build_summary_message(title: str, expenses: list[dict], currency: str) -> str:
    """Build a formatted summary from a list of expense rows."""
    if not expenses:
        return f"{title}\n\n😌 No expenses logged for this period."

    # Group by category
    by_category: dict[str, float] = {}
    total = 0.0
    for exp in expenses:
        cat = exp["category"]
        amt = exp["amount"]
        by_category[cat] = by_category.get(cat, 0) + amt
        total += amt

    # Sort by amount descending
    sorted_cats = sorted(by_category.items(), key=lambda x: x[1], reverse=True)

    lines = [title, ""]
    for cat, amount in sorted_cats:
        emoji = _category_emoji(cat)
        pct = (amount / total * 100) if total > 0 else 0
        if amount == int(amount):
            amt_str = f"{int(amount):,}"
        else:
            amt_str = f"{amount:,.2f}"
        lines.append(f"  {emoji} {cat.capitalize()}: *{amt_str} {currency}* ({pct:.0f}%)")

    lines.append("")
    if total == int(total):
        total_str = f"{int(total):,}"
    else:
        total_str = f"{total:,.2f}"
    lines.append(f"💰 *Total: {total_str} {currency}*")
    lines.append(f"📝 {len(expenses)} transaction{'s' if len(expenses) > 1 else ''}")

    return "\n".join(lines)


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /today — show today's expenses."""
    user = update.effective_user
    db_user = await get_or_create_user(telegram_user_id=user.id)

    today = str(date.today())
    expenses = await get_expenses_by_range(db_user["id"], today, today)

    msg = _build_summary_message("📅 *Today's Spending*", expenses, db_user["currency"])
    await update.message.reply_text(msg, parse_mode="Markdown")


async def week_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /week — show last 7 days."""
    user = update.effective_user
    db_user = await get_or_create_user(telegram_user_id=user.id)

    today = date.today()
    week_ago = today - timedelta(days=6)
    expenses = await get_expenses_by_range(db_user["id"], str(week_ago), str(today))

    title = f"📊 *Last 7 Days* ({week_ago.strftime('%b %d')} – {today.strftime('%b %d')})"
    msg = _build_summary_message(title, expenses, db_user["currency"])
    await update.message.reply_text(msg, parse_mode="Markdown")


async def month_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /month — show current month."""
    user = update.effective_user
    db_user = await get_or_create_user(telegram_user_id=user.id)

    today = date.today()
    start = today.replace(day=1)
    expenses = await get_expenses_by_range(db_user["id"], str(start), str(today))

    title = f"📆 *{today.strftime('%B %Y')}*"
    msg = _build_summary_message(title, expenses, db_user["currency"])
    await update.message.reply_text(msg, parse_mode="Markdown")


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /report — generate an AI-powered monthly coaching report."""
    user = update.effective_user
    db_user = await get_or_create_user(telegram_user_id=user.id)

    await update.message.chat.send_action("typing")

    today = date.today()
    summary = await get_monthly_summary(db_user["id"], today.year, today.month)

    if summary["total_spent"] == 0:
        await update.message.reply_text(
            "📊 No expenses logged this month yet. Start tracking and come back later!"
        )
        return

    # Get previous month for comparison
    if today.month == 1:
        prev_year, prev_month = today.year - 1, 12
    else:
        prev_year, prev_month = today.year, today.month - 1

    prev_summary = await get_monthly_summary(db_user["id"], prev_year, prev_month)
    prev_total = prev_summary["total_spent"] if prev_summary["total_spent"] > 0 else None

    report = await generate_monthly_report(summary, previous_month_total=prev_total)

    await update.message.reply_text(
        f"📊 *Monthly Report — {today.strftime('%B %Y')}*\n\n{report}",
        parse_mode="Markdown",
    )
