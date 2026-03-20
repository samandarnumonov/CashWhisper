"""Handlers for expense logging — voice and text messages."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from database import get_or_create_user, save_expenses
from services.transcriber import transcribe_voice
from services.parser import parse_expenses

logger = logging.getLogger(__name__)


def _format_confirmation(expenses: list[dict]) -> str:
    """Build a nice confirmation message from parsed expenses."""
    if not expenses:
        return "couldn't find expenses in your message."

    lines = []
    total_by_currency: dict[str, float] = {}

    for exp in expenses:
        amt = exp["amount"]
        cur = exp["currency"]
        cat = exp["category"]
        desc = exp.get("description", "")

        # Format amount nicely
        if amt == int(amt):
            amt_str = f"{int(amt):,}"
        else:
            amt_str = f"{amt:,.2f}"

        line = f"· {amt_str} {cur}  {desc}" if desc else f"· {amt_str} {cur}  {cat}"
        lines.append(line)

        total_by_currency[cur] = total_by_currency.get(cur, 0) + amt

    count = len(expenses)
    header = f"✓ {count} expense{'s' if count > 1 else ''} saved\n"

    # Total line
    totals = []
    for cur, total in total_by_currency.items():
        if total == int(total):
            totals.append(f"{int(total):,} {cur}")
        else:
            totals.append(f"{total:,.2f} {cur}")

    footer = f"\n{'—' * 18}\n  {' + '.join(totals)}  total"

    return header + "\n" + "\n".join(lines) + footer



async def handle_text_expense(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle plain text messages — parse as expense input."""
    user = update.effective_user
    text = update.message.text.strip()

    if not text:
        return

    # Ensure user exists
    db_user = await get_or_create_user(
        telegram_user_id=user.id,
        username=user.username,
        first_name=user.first_name,
    )

    # Send typing indicator
    await update.message.chat.send_action("typing")

    try:
        expenses = await parse_expenses(text, base_currency=db_user["currency"])
    except Exception as e:
        logger.error("Error parsing expenses for user %s: %s", user.id, e)
        await update.message.reply_text(
            "⚠️ Sorry, I had trouble understanding that. Please try again!"
        )
        return

    if expenses:
        await save_expenses(
            user_id=db_user["id"],
            expenses=expenses,
            source="text",
            raw_input=text,
        )

    reply = _format_confirmation(expenses)
    await update.message.reply_text(reply)


async def handle_voice_expense(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice messages — transcribe then parse as expenses."""
    user = update.effective_user

    # Ensure user exists
    db_user = await get_or_create_user(
        telegram_user_id=user.id,
        username=user.username,
        first_name=user.first_name,
    )

    await update.message.chat.send_action("typing")

    # Download the voice file
    voice = update.message.voice or update.message.audio
    if not voice:
        await update.message.reply_text("couldn't read that audio.")
        return

    try:
        file = await context.bot.get_file(voice.file_id)
        audio_bytes = await file.download_as_bytearray()
    except Exception as e:
        logger.error("Failed to download voice for user %s: %s", user.id, e)
        await update.message.reply_text("couldn't download your voice message.")
        return

    # Transcribe
    try:
        transcript = await transcribe_voice(bytes(audio_bytes))
    except Exception as e:
        logger.error("Transcription failed for user %s: %s", user.id, e)
        await update.message.reply_text("couldn't transcribe your voice message.")
        return

    if not transcript:
        await update.message.reply_text("couldn't hear anything in that message.")
        return

    # Parse expenses from transcript
    try:
        expenses = await parse_expenses(transcript, base_currency=db_user["currency"])
    except Exception as e:
        logger.error("Error parsing expenses for user %s: %s", user.id, e)
        await update.message.reply_text("sorry, i couldn't understand that.")
        return

    if expenses:
        await save_expenses(
            user_id=db_user["id"],
            expenses=expenses,
            source="voice",
            raw_input=transcript,
        )

    # Build reply with transcription preview
    transcript_preview = transcript[:100] + ("..." if len(transcript) > 100 else "")
    reply = f'"{transcript_preview}"\n\n' + _format_confirmation(expenses)
    await update.message.reply_text(reply)
