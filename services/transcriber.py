"""Groq Whisper transcription service (OpenAI-compatible API)."""

import tempfile
import os
from openai import AsyncOpenAI
from config import GROQ_API_KEY, GROQ_BASE_URL, GROQ_WHISPER_MODEL

_client = AsyncOpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)


async def transcribe_voice(audio_bytes: bytes, filename: str = "voice.ogg") -> str:
    """
    Transcribe audio bytes using Groq's Whisper endpoint.
    Returns the transcript text.
    """
    suffix = os.path.splitext(filename)[1] or ".ogg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as audio_file:
            response = await _client.audio.transcriptions.create(
                model=GROQ_WHISPER_MODEL,
                file=audio_file,
                response_format="text",
            )
        return response.strip()
    finally:
        os.unlink(tmp_path)
