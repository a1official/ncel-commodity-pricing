from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from pydantic import BaseModel

from ...core.database import get_db
from ...services.chatbot_service import ChatbotService

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    language: str = "en"
    history: List[Dict[str, str]] = []

class ChatResponse(BaseModel):
    text: str
    intent: str
    commodity: str | None
    data: Any | None

@router.post("/chat", response_model=ChatResponse, tags=["Chatbot"])
def chat_with_bot(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Interact with the commodity intelligence chatbot.
    Detects language, extracts intent, applies multi-signal forecasting and price aggregation.
    """
    chatbot = ChatbotService(db)
    response = chatbot.get_response(request.query, request.language, request.history)
    
    return {
        "text": response["text"],
        "intent": response["intent"],
        "commodity": response["commodity"],
        "data": response.get("data")
    }
