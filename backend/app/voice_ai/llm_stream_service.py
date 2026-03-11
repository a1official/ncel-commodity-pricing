import json
import logging
from typing import Any, AsyncGenerator

from groq import AsyncGroq
from ..core.config import settings

logger = logging.getLogger(__name__)

class LLMStreamService:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.client = AsyncGroq(api_key=self.api_key) if self.api_key else None

    async def generate_streaming_response(self, text: str, data_context: Any = None, lang: str = "en", history: list = []) -> AsyncGenerator[str, None]:
        """Streams text chunks from the Groq LLM model in real time."""
        if not self.client:
            yield "LLM service is not configured. Missing GROQ_API_KEY."
            return

        context_str = json.dumps(data_context) if data_context else "No extra data."
        system_prompt = (
            f"CRITICAL: YOU MUST RESPOND IN THE FOLLOWING LANGUAGE: {lang}.\n"
            f"You are a helpful AI market analyst. Respond to the user's voice prompt in {lang}.\n"
            "Keep the answer concise and suitable for spoken dialogue (no complex markdown, avoid * and ** symbols).\n"
            f"Context data: {context_str}"
        )

        # Format history to LLM format
        formatted_history = []
        for msg in history:
            role = "assistant" if msg.get("role") == "bot" else msg.get("role", "user")
            content = msg.get("text") or msg.get("content") or ""
            if content:
                formatted_history.append({"role": role, "content": content})

        try:
            stream = await self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    *formatted_history,
                    {"role": "user", "content": text}
                ],
                stream=True,
                max_tokens=250,
                temperature=0.3
            )
            
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    # Clean markdown symbols for better TTS
                    cleaned_content = content.replace('*', '').replace('#', '')
                    yield cleaned_content

        except Exception as e:
            logger.error(f"LLM Stream Error: {e}")
            yield f" Sorry, I encountered an error: {str(e)}"
