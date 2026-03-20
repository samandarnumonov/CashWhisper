"""Groq LLM expense extraction service (OpenAI-compatible API)."""

import json
import logging
from datetime import date
from openai import AsyncOpenAI
from config import GROQ_API_KEY, GROQ_BASE_URL, GROQ_CHAT_MODEL

logger = logging.getLogger(__name__)

_client = AsyncOpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)

SYSTEM_PROMPT = """You are an assistant that extracts personal expenses from short messages.
Always respond with valid JSON only. Do not include explanations or any extra text.

Rules:
- When the user says "k" after a number, treat it as thousands (e.g. "80k" = 80000).
- Assign a category from this list: food, transport, groceries, shopping, bills, subscriptions, entertainment, health, education, other.
- If the currency isn't explicitly stated, use the base currency provided.
- If no date is mentioned, use the current date provided.
- "description" should be a short label for what was purchased.
- Always return a JSON object with an "expenses" array."""

USER_PROMPT_TEMPLATE = """Text: "{text}"
Base currency: {currency}
Current date: {current_date}

Return JSON with this schema:
{{
  "expenses": [
    {{
      "amount": number,
      "currency": string,
      "category": string,
      "description": string,
      "date": "YYYY-MM-DD"
    }}
  ]
}}"""


async def parse_expenses(
    text: str,
    base_currency: str = "UZS",
    current_date: str | None = None,
) -> list[dict]:
    """
    Send text to Groq LLM and extract structured expenses.
    Returns a list of expense dicts: [{amount, currency, category, description, date}]
    """
    if current_date is None:
        current_date = str(date.today())

    user_prompt = USER_PROMPT_TEMPLATE.format(
        text=text,
        currency=base_currency,
        current_date=current_date,
    )

    try:
        response = await _client.chat.completions.create(
            model=GROQ_CHAT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        data = json.loads(content)
        expenses = data.get("expenses", [])

        # Validate each expense has required fields
        validated = []
        for exp in expenses:
            if "amount" in exp and "currency" in exp and "category" in exp:
                validated.append({
                    "amount": float(exp["amount"]),
                    "currency": str(exp["currency"]),
                    "category": str(exp["category"]).lower(),
                    "description": str(exp.get("description", "")),
                    "date": str(exp.get("date", current_date)),
                })

        return validated

    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.error("Failed to parse LLM response: %s", e)
        return []
    except Exception as e:
        logger.error("Groq API error during parsing: %s", e)
        raise
