"""Callback query handlers for inline keyboards (Accept/Reject)."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from database import update_expense_status, get_or_create_user

logger = logging.getLogger(__name__)


async def handle_expense_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Accept/Reject expense callbacks."""
    query = update.callback_query
    await query.answer()

    # Escape any Markdown formatting from plain text to prevent parse errors
    def escape_markdown(text: str) -> str:
        for c in ['*', '_', '`', '[']:
            text = text.replace(c, f"\\{c}")
        return text

    user = update.effective_user
    db_user = await get_or_create_user(telegram_user_id=user.id)
    data = query.data
    safe_text = escape_markdown(query.message.text) if query.message.text else "Expense"

    if data.startswith("exp_acc:"):
        message_id = int(data.split(":")[1])
        # Mark as confirmed
        updated = await update_expense_status(db_user["id"], message_id, "confirmed")
        logger.info("Accepting expense: msg_id=%s, db_user=%s, updated rows=%s", message_id, db_user["id"], updated)
        if updated > 0:
            # Edit message to remove keyboard and append confirmation text
            new_text = safe_text + "\n\n✅ *Confirmed and saved!*"
            await query.edit_message_text(text=new_text, parse_mode="Markdown")
        else:
            new_text = safe_text + "\n\n⚠️ Could not find pending expenses\\. Maybe already processed?"
            await query.edit_message_text(text=new_text, parse_mode="Markdown")

    elif data.startswith("exp_rej:"):
        message_id = int(data.split(":")[1])
        # Mark as rejected
        updated = await update_expense_status(db_user["id"], message_id, "rejected")
        logger.info("Rejecting expense: msg_id=%s, db_user=%s, updated rows=%s", message_id, db_user["id"], updated)
        if updated > 0:
            # Edit message to remove keyboard and append rejection text
            new_text = safe_text + "\n\n❌ *Rejected! Please type or speak it again correctly.*"
            await query.edit_message_text(text=new_text, parse_mode="Markdown")
        else:
            new_text = safe_text + "\n\n⚠️ Could not find pending expenses\\. Maybe already processed?"
            await query.edit_message_text(text=new_text, parse_mode="Markdown")
