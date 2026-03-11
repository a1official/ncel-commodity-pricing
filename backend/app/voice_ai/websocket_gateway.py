import io
import asyncio
import json
import traceback
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .stt_service import STTService
from .llm_stream_service import LLMStreamService
from .tts_stream_service import TTSService
from ..services.chatbot_service import ChatbotService
from ..core.database import SessionLocal

router = APIRouter()

stt_service = STTService()
llm_service = LLMStreamService()
tts_service = TTSService()

@router.websocket("/ws/voice-chat")
async def voice_chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    audio_buffer = bytearray()
    
    # 1. Background task to stream TTS audio to websocket as it becomes ready
    tts_queue = asyncio.Queue()

    async def tts_worker(lang_code):
        """Worker that processes sentences from the queue and sends audio bytes."""
        try:
            while True:
                sentence = await tts_queue.get()
                if sentence is None: break # Shutdown signal
                
                async for audio_bytes in tts_service.stream_audio_from_text(sentence, language_code=lang_code):
                    await websocket.send_bytes(audio_bytes)
                tts_queue.task_done()
        except Exception as e:
            print(f"TTS Worker Error: {e}")

    # Map frontend languages to Sarvam codes
    LANGUAGE_MAP = {
        "English": "en-IN", "Hindi": "hi-IN", "Marathi": "mr-IN",
        "Gujarati": "gu-IN", "Tamil": "ta-IN", "Telugu": "te-IN", "Bengali": "bn-IN"
    }

    try:
        while True:
            message = await websocket.receive()
            
            if "text" in message:
                try:
                    meta = json.loads(message["text"])
                    lang_name = meta.get("language", "English")
                    tts_lang_code = LANGUAGE_MAP.get(lang_name, "en-IN")

                    if meta.get("type") == "init_call":
                        greetings = {
                            "English": "Hello! I am your Market Analyst A.I. How can I help you today?",
                            "Hindi": "नमस्ते! मैं आपका मार्केट एनालिस्ट ए.आई हूं। मैं आज आपकी कैसे मदद कर सकता हूं?",
                            "Marathi": "नमस्कार! मी तुमचा मार्केट अॅनालिस्ट ए.आय. आहे. मी तुम्हाला कशी मदत करू शकतो?",
                            "Gujarati": "નમસ્તે! હું તમારો માર્કેટ એનાલિસ્ટ એ.આઈ. છું. હું આજે તમને કેવી રીતે મદદ કરી શકું?",
                            "Tamil": "வணக்கம்! நான் உங்கள் சந்தை ஆய்வாளர் ஏ.ஐ. இன்று நான் உங்களுக்கு எப்படி உதவ முடியும்?",
                            "Telugu": "నమస్కారం! నేను మీ మార్కెట్ అనలిస్ట్ ఏ.ఐ. ఈ రోజు నేను మీకు ఎలా సహాయపడగలను?",
                            "Bengali": "নমস্কার! আমি আপনার মার্কেট অ্যানালিস্ট এ.আই. আজ আমি আপনাকে কীভাবে সাহায্য করতে পারি?"
                        }
                        greeting = greetings.get(lang_name, greetings["English"])
                        
                        await websocket.send_json({"type": "transcript", "text": "*(Call Connected)*"})
                        await websocket.send_json({"type": "llm_start"})
                        
                        # Start worker for this greeting
                        async for audio_bytes in tts_service.stream_audio_from_text(greeting, language_code=tts_lang_code):
                            await websocket.send_bytes(audio_bytes)
                            
                        await websocket.send_json({"type": "llm_end", "full_text": greeting})
                        
                    elif meta.get("type") == "audio_end":
                        # Process clip
                        transcript_text = await stt_service.transcribe_audio(bytes(audio_buffer))
                        audio_buffer.clear()
                        
                        if not transcript_text:
                            await websocket.send_json({"type": "error", "message": "Could not hear anything."})
                            continue
                            
                        await websocket.send_json({"type": "transcript", "text": transcript_text})
                        
                        # 2. Optimized Context Fetching (Data Context Only)
                        db = SessionLocal()
                        assistant = ChatbotService(db)
                        history = meta.get("history", [])
                        bot_res = assistant.get_data_context(transcript_text, language=lang_name, history=history)
                        db.close()
                        
                        await websocket.send_json({"type": "llm_start"})
                        
                        # 3. Parallelize LLM Streaming and TTS Generation
                        # We start the worker to handle the queue
                        worker_task = asyncio.create_task(tts_worker(tts_lang_code))
                        
                        full_llm_text = ""
                        sentence_buffer = ""
                        
                        async for token in llm_service.generate_streaming_response(transcript_text, bot_res["data"], lang=lang_name, history=history):
                            full_llm_text += token
                            sentence_buffer += token
                            await websocket.send_json({"type": "llm_chunk", "text": token})
                            
                            # Detect sentence end and push to TTS queue without waiting
                            if any(p in token for p in [".", "?", "!", "\n", ":"]):
                                text_to_speak = sentence_buffer.strip()
                                if text_to_speak:
                                    await tts_queue.put(text_to_speak)
                                sentence_buffer = ""

                        # Flush remaining
                        if sentence_buffer.strip():
                            await tts_queue.put(sentence_buffer.strip())
                            
                        # Wait for all sentences to be processed by TTS worker
                        await tts_queue.put(None) # Signal worker to exit after finishing queue
                        await worker_task
                                
                        await websocket.send_json({"type": "llm_end", "full_text": full_llm_text})
                        
                except Exception as e:
                    print(f"WS Logic Error: {e}")
                    traceback.print_exc()

            elif "bytes" in message:
                audio_buffer.extend(message["bytes"])

    except WebSocketDisconnect:
        print("Voice WebSocket disconnected.")
    except Exception as e:
        print(f"Voice WebSocket error: {e}")
