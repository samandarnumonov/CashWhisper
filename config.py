"""CashWhisper configuration — loads environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DATABASE_PATH = os.getenv("DATABASE_PATH", "cashwhisper.db")

# Groq API settings (OpenAI-compatible)
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_CHAT_MODEL = os.getenv("GROQ_CHAT_MODEL", "llama-3.3-70b-versatile")
GROQ_WHISPER_MODEL = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3")

# Validate required keys
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set. Check your .env file.")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set. Check your .env file.")
