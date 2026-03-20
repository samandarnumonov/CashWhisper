"""Groq LLM monthly report / budget coach service."""

import json
import logging
from openai import AsyncOpenAI
from config import GROQ_API_KEY, GROQ_BASE_URL, GROQ_CHAT_MODEL

logger = logging.getLogger(__name__)

_client = AsyncOpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)

SYSTEM_PROMPT = """You are a friendly budget coach. Given a user's monthly spending stats,
explain clearly where their money went and suggest 2–3 practical actions to improve.
Keep your answer under 200 words. Use emoji to make the message feel friendly.
Format your response nicely for a Telegram chat (use bold with *text*, and line breaks)."""


async def generate_monthly_report(
    summary: dict,
    previous_month_total: float | None = None,
) -> str:
    """
    Generate a human-friendly monthly spending report using Groq LLM.

    summary: {month, total_spent, currency, categories: [{name, amount}]}
    Returns a string message ready to send to the user.
    """
    report_data = {
        "month": summary["month"],
        "total_spent": summary["total_spent"],
        "currency": summary["currency"],
        "categories": summary["categories"],
    }
    if previous_month_total is not None:
        report_data["comparison"] = {
            "previous_month_total": previous_month_total,
        }

    try:
        response = await _client.chat.completions.create(
            model=GROQ_CHAT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Here is the spending data:\n{json.dumps(report_data, indent=2)}",
                },
            ],
            temperature=0.7,
            max_tokens=500,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error("Failed to generate monthly report: %s", e)
        return (
            f"📊 *Monthly Report — {summary['month']}*\n\n"
            f"Total spent: {summary['total_spent']:,.0f} {summary['currency']}\n\n"
            "_(Detailed AI summary unavailable right now.)_"
        )
