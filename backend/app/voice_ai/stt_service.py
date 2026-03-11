import io
import logging
from groq import AsyncGroq
from ..core.config import settings

logger = logging.getLogger(__name__)

class STTService:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.client = AsyncGroq(api_key=self.api_key) if self.api_key else None

    async def transcribe_audio(self, audio_bytes: bytes) -> str:
        """
        Uses Groq Whisper to transcribe the received audio bytes into text.
        """
        if not self.client:
            return "Speech text transcription is missing GROQ_API_KEY"
            
        try:
            # Wrap bytes in BytesIO
            file_tuple = ("audio.webm", io.BytesIO(audio_bytes), "audio/webm")
            
            result = await self.client.audio.transcriptions.create(
                file=file_tuple,
                model="whisper-large-v3",
                language="en", 
                temperature=0.0
            )
            return result.text
        except Exception as e:
            logger.error(f"Whisper STT Error: {e}")
            return f"Error transcribing: {str(e)}"
