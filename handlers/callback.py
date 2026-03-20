"""Callback query handlers for inline keyboards (Accept/Reject)."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from database import update_expense_status

logger = logging.getLogger(__name__)


async def handle_expense_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Accept/Reject expense callbacks."""
    query = update.callback_query
    # Answer the query to stop the loading animation on the button
    await query.answer()

    user = update.effective_user
    data = query.data

    if data.startswith("exp_acc:"):
        message_id = int(data.split(":")[1])
        # Mark as confirmed
        updated = await update_expense_status(user.id, message_id, "confirmed")
        if updated > 0:
            # Edit message to remove keyboard and append confirmation text
            new_text = query.message.text + "\n\n✅ *Confirmed and saved!*"
            # We must handle formatting properly if query.message.text lost Markdown bold chars, 
            # but usually it's plain text here. We'll just append.
            await query.edit_message_text(text=new_text)
        else:
            await query.edit_message_text(text=query.message.text + "\n\n⚠️ Could not find pending expenses. Maybe already processed?")

    elif data.startswith("exp_rej:"):
        message_id = int(data.split(":")[1])
        # Mark as rejected
        updated = await update_expense_status(user.id, message_id, "rejected")
        if updated > 0:
            # Edit message to remove keyboard and append rejection text
            new_text = query.message.text + "\n\n❌ *Rejected! Please type or speak it again correctly.*"
            await query.edit_message_text(text=new_text)
        else:
            await query.edit_message_text(text=query.message.text + "\n\n⚠️ Could not find pending expenses. Maybe already processed?")
