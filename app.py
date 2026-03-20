"""
CashWhisper — Telegram voice-first expense tracker & budget coach
Entry point: initializes DB, registers handlers, starts polling.
"""

import asyncio
import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN, DATABASE_PATH
from database import init_db, set_db_path
from handlers.start import (
    start_command,
    help_command,
    settings_command,
    currency_command,
    timezone_command,
    reminder_command,
)
from handlers.expense import handle_text_expense, handle_voice_expense
from handlers.summary import today_command, week_command, month_command, report_command
from scheduler import daily_reminder_job, monthly_report_job

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("cashwhisper")


def main() -> None:
    """Start the CashWhisper bot."""

    # Database
    set_db_path(DATABASE_PATH)

    # Build application
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # ── Register command handlers ────────────────────────────────────
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("currency", currency_command))
    app.add_handler(CommandHandler("timezone", timezone_command))
    app.add_handler(CommandHandler("reminder", reminder_command))
    app.add_handler(CommandHandler("today", today_command))
    app.add_handler(CommandHandler("week", week_command))
    app.add_handler(CommandHandler("month", month_command))
    app.add_handler(CommandHandler("report", report_command))

    # ── Register message handlers ────────────────────────────────────
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice_expense))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_expense))

    # ── Schedule jobs ────────────────────────────────────────────────
    job_queue = app.job_queue
    if job_queue:
        # Daily reminder check — runs every 60 seconds
        job_queue.run_repeating(
            daily_reminder_job,
            interval=60,
            first=10,
            name="daily_reminder",
        )
        # Monthly report — runs once a day at 09:00 UTC
        from datetime import time as dt_time
        job_queue.run_daily(
            monthly_report_job,
            time=dt_time(hour=9, minute=0),
            name="monthly_report",
        )
        logger.info("Scheduled jobs: daily_reminder (every 60s), monthly_report (09:00 UTC)")
    else:
        logger.warning("JobQueue not available — reminders and reports will not be sent.")

    # ── Initialize DB and start polling ───────────────────────────────
    async def post_init(application) -> None:
        await init_db()
        logger.info("Database initialized at %s", DATABASE_PATH)

    app.post_init = post_init

    logger.info("🚀 CashWhisper bot is starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    # Python 3.14+ requires an explicit event loop
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    main()
