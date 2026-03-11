import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import func
from groq import Groq

from ..models import models
from ..services.forecasting_enhanced import MultiSignalForecaster
from ..core.config import settings

COMMODITIES_LIST = [
    "Rice", "Wheat", "Maize", "Groundnut", "Turmeric", "Chilli", "Cumin", 
    "Onion", "Tomato", "Potato", "Banana", "Grapes", "Pineapple", "Millets", 
    "Shrimp", "Mackerel", "Tuna", "Trout", "Soybean", "Sugar", "Cotton"
]

class ChatbotService:
    def __init__(self, db: Session):
        self.db = db
        self.forecaster = MultiSignalForecaster(db)
        
        self.api_key = settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY", "")
        if self.api_key:
            self.client = Groq(api_key=self.api_key)
        else:
            self.client = None

    def _get_commodity_from_db(self, commodity_name: str) -> Optional[models.Commodity]:
        if not commodity_name:
            return None
        return self.db.query(models.Commodity).filter(
            models.Commodity.name.ilike(f"%{commodity_name}%")
        ).first()

    def _format_history(self, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Transforms frontend history format to LLM message format."""
        formatted = []
        for msg in history:
            role = msg.get("role")
            if role == "bot":
                role = "assistant"
            
            content = msg.get("text") or msg.get("content") or ""
            if content:
                formatted.append({"role": role, "content": content})
        return formatted

    def process_with_llm(self, query: str, language: str = "en", history: List[Dict[str, str]] = []) -> Dict[str, Any]:
        """
        Uses Groq LLM to parse intent, commodity, and parameters via JSON mode.
        """
        if not self.client:
            return {
                "intent": "error",
                "text": "Please configure GROQ_API_KEY to use the chat assistant.",
                "commodity": None,
                "data": None
            }

        system_prompt = (
            f"CRITICAL: YOU MUST RESPOND IN THE FOLLOWING LANGUAGE: {language}.\n"
            "You are a market analyst assistant. Your job is to extract the user's intent and target commodity. "
            f"Allowed commodities: {', '.join(COMMODITIES_LIST)}.\n"
            "Allowed intents: 'price', 'forecast', 'trend', or 'general'.\n"
            "If the user is just saying hello or asking a non-commodity question, set intent to 'general'.\n"
            "Respond ONLY with a valid JSON object in this exact format:\n"
            '{"intent": "price|forecast|trend|general", "commodity": "CommodityName or null", "reply": "A friendly reply in the requested language (e.g. Hindi if asked)"}'
        )

        formatted_history = self._format_history(history)

        try:
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    *formatted_history,
                    {"role": "user", "content": query}
                ],
                response_format={"type": "json_object"},
                max_tokens=300
            )

            result = json.loads(response.choices[0].message.content)
            
            intent = result.get("intent", "general")
            commodity = result.get("commodity")
            
            if intent == "general" or not commodity:
                return {
                    "action": "direct_reply",
                    "intent": "general",
                    "text": result.get("reply", "Hello! I am your AI Market Analyst. I can provide real-time prices, forecasts, and trends across 21 commodities. How can I help you today?"),
                    "commodity": None,
                    "data": None
                }
            
            return {
                "action": "execute_tool",
                "intent": intent,
                "commodity": commodity
            }
                
        except Exception as e:
            return {
                "action": "error",
                "intent": "error",
                "text": f"Error parsing query with Groq: {str(e)}",
                "commodity": None,
                "data": None
            }

    def generate_final_response(self, intent: str, commodity_name: str, query: str, data: Any, language: str = "en", history: List[Dict[str, str]] = []) -> str:
        """
        Produce a professional formatted answer in the specified language using the fetched data.
        """
        if not self.client:
            return "Please provide a valid Groq API key."
            
        system_prompt = (
            f"CRITICAL: YOU MUST RESPOND IN THE FOLLOWING LANGUAGE: {language}.\n"
            "You are a professional market analyst for a Commodity Intelligence Platform. "
            "Your task is to take the raw data provided below and formulate a helpful, factual response to the user's query. "
            "Rules:\n"
            "- Be descriptive and concise.\n"
            f"- YOU MUST answer in {language}.\n"
            "- If the data shows an error or no data, politely mention that no data is available for that period/commodity.\n"
            "- Format nicely. Act like a helpful financial analyst."
        )
        
        data_context = json.dumps(data)
        prompt = (
            f"User Query: {query}\n"
            f"Intent: {intent}\n"
            f"Commodity: {commodity_name}\n"
            f"Raw Data Context: {data_context}\n\n"
            f"Write the response now."
        )

        formatted_history = self._format_history(history)

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    *formatted_history,
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Data retrieved, but failed to format response: {str(e)}"

    def get_data_context(self, query: str, language: str = "en", history: List[Dict[str, str]] = []) -> Dict[str, Any]:
        """Modified version of get_response that only fetches the data without generating final text."""
        parsed = self.process_with_llm(query, language, history)
        if parsed.get("action") != "execute_tool":
            return {"intent": parsed.get("intent", "general"), "commodity": None, "data": None}
            
        intent = parsed.get("intent")
        commodity_name = parsed.get("commodity")
        commodity = self._get_commodity_from_db(commodity_name)
        
        if not commodity:
            return {"intent": intent, "commodity": commodity_name, "data": None}
            
        data_to_pass = None
        if intent == "price":
            latest_price = self.db.query(models.PriceRecord).filter(
                models.PriceRecord.commodity_id == commodity.id
            ).order_by(models.PriceRecord.date.desc()).first()
            if latest_price:
                data_to_pass = {"price": float(latest_price.modal_price), "date": latest_price.date.isoformat(), "unit": "per quintal"}
        elif intent == "forecast":
            data_to_pass = self.forecaster.get_forecast(commodity.id, 6)
        elif intent == "trend":
            cutoff_date = datetime.now().date()
            start_date = cutoff_date - timedelta(days=21)
            prices = self.db.query(models.PriceRecord).filter(
                models.PriceRecord.commodity_id == commodity.id,
                models.PriceRecord.date >= start_date
            ).order_by(models.PriceRecord.date.asc()).all()
            if prices:
                start_p = float(prices[0].modal_price)
                end_p = float(prices[-1].modal_price)
                if start_p > 0:
                    data_to_pass = {"start_price": start_p, "current_price": end_p, "change_percentage": round(((end_p - start_p)/start_p)*100), "period": "3 weeks"}

        return {"intent": intent, "commodity": commodity.name, "data": data_to_pass}

    def get_response(self, query: str, language: str = "en", history: List[Dict[str, str]] = []) -> Dict[str, Any]:
        print(f"DEBUG: Processing query '{query}' in language '{language}'")
        
        # 1. Parse intent and commodity via LLM
        parsed = self.process_with_llm(query, language, history)
        print("LLM Parsed Response:", parsed)
        
        if parsed.get("action") == "error":
            return {"text": parsed["text"], "intent": "error", "commodity": None, "data": None}
        if parsed.get("action") == "direct_reply":
            return {"text": parsed["text"], "intent": parsed["intent"], "commodity": None, "data": None}

        intent = parsed.get("intent")
        commodity_name = parsed.get("commodity")
        
        commodity = self._get_commodity_from_db(commodity_name)
        if not commodity:
            if not commodity_name:
                return {
                    "text": "Please specify which commodity you are asking about (e.g., Rice, Wheat).",
                    "intent": intent,
                    "commodity": None,
                    "data": None
                }
            return {
                "text": f"I cannot find '{commodity_name}' in my tracked list of commodities.",
                "intent": intent,
                "commodity": commodity_name,
                "data": None
            }
            
        data_to_pass = None
        
        # 2. Execute business logic based on intent
        if intent == "price":
            latest_price = self.db.query(models.PriceRecord).filter(
                models.PriceRecord.commodity_id == commodity.id
            ).order_by(models.PriceRecord.date.desc()).first()
            
            if latest_price:
                data_to_pass = {
                    "price": float(latest_price.modal_price),
                    "date": latest_price.date.isoformat(),
                    "unit": "per quintal"
                }
            else:
                data_to_pass = {"error": "No price data found"}
                
        elif intent == "forecast":
            forecast = self.forecaster.get_forecast(commodity.id, 6)
            data_to_pass = forecast
            
        elif intent == "trend":
            cutoff_date = datetime.now().date()
            start_date = cutoff_date - timedelta(days=21)
            prices = self.db.query(models.PriceRecord).filter(
                models.PriceRecord.commodity_id == commodity.id,
                models.PriceRecord.date >= start_date
            ).order_by(models.PriceRecord.date.asc()).all()
            
            if prices:
                start_price = float(prices[0].modal_price)
                end_price = float(prices[-1].modal_price)
                if start_price > 0:
                    change_pct = round(((end_price - start_price) / start_price) * 100)
                    data_to_pass = {
                        "start_price": start_price,
                        "current_price": end_price,
                        "change_percentage": change_pct,
                        "period": "3 weeks"
                    }
            if not data_to_pass:
                data_to_pass = {"error": "Not enough historical data"}
                
        # 3. Generate final conversational response using the data
        final_text = self.generate_final_response(intent, commodity.name, query, data_to_pass, language, history)
        
        return {
            "text": final_text,
            "intent": intent,
            "commodity": commodity.name,
            "data": data_to_pass
        }
