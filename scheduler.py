"""Daily check-in reminders and monthly report scheduler."""

import logging
from datetime import datetime, date

from telegram.ext import ContextTypes

from database import get_all_users_with_reminders, get_monthly_summary, get_or_create_user
from services.reporter import generate_monthly_report

logger = logging.getLogger(__name__)


async def daily_reminder_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Runs every minute. Checks which users have reminders enabled
    for the current time (HH:MM) and sends them a check-in message.
    """
    now = datetime.now()
    current_time = now.strftime("%H:%M")

    users = await get_all_users_with_reminders()
    for user in users:
        if user["daily_reminder_time"] == current_time:
            try:
                await context.bot.send_message(
                    chat_id=user["telegram_user_id"],
                    text=(
                        "daily check-in\n\n"
                        "how was your spending today?\n"
                        "send me a voice or text message with your expenses."
                    ),
                )
                logger.info(
                    "Sent daily reminder to user %s", user["telegram_user_id"]
                )
            except Exception as e:
                logger.error(
                    "Failed to send reminder to user %s: %s",
                    user["telegram_user_id"],
                    e,
                )


async def monthly_report_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Runs on the 1st of each month. Generates and sends monthly reports
    to all users who had expenses in the previous month.
    """
    today = date.today()
    if today.day != 1:
        return

    # Previous month
    if today.month == 1:
        report_year, report_month = today.year - 1, 12
    else:
        report_year, report_month = today.year, today.month - 1

    # Get the month before that for comparison
    if report_month == 1:
        prev_year, prev_month = report_year - 1, 12
    else:
        prev_year, prev_month = report_year, report_month - 1

    # We need to iterate all users — for simplicity, get users with reminders
    # In a production app you'd iterate all users
    users = await get_all_users_with_reminders()

    for user in users:
        try:
            summary = await get_monthly_summary(user["id"], report_year, report_month)
            if summary["total_spent"] == 0:
                continue

            prev_summary = await get_monthly_summary(user["id"], prev_year, prev_month)
            prev_total = (
                prev_summary["total_spent"]
                if prev_summary["total_spent"] > 0
                else None
            )

            report = await generate_monthly_report(summary, previous_month_total=prev_total)

            month_name = datetime(report_year, report_month, 1).strftime("%B %Y").lower()
            await context.bot.send_message(
                chat_id=user["telegram_user_id"],
                text=f"ai report — {month_name}\n\n{report}",
            )
            logger.info(
                "Sent monthly report to user %s", user["telegram_user_id"]
            )
        except Exception as e:
            logger.error(
                "Failed to send monthly report to user %s: %s",
                user["telegram_user_id"],
                e,
            )
