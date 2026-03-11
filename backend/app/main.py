import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.v1.endpoints_enhanced import router as api_router
from .api.v1.chatbot import router as chatbot_router
from .api.v1.websocket import manager as ws_manager
from .voice_ai.websocket_gateway import router as voice_ws_router
from .ingestion.connectors_enhanced import NCDEXConnector, MCXConnector
from .ingestion.pipeline_orchestrator import commodity_ingestion_pipeline
from .core.config import settings
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set all CORS enabled origins
origins = settings.CORS_ORIGINS
if isinstance(origins, str):
    origins = [origin.strip() for origin in origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def schedule_ingestion():
    """Background task to run ingestion every 24 hours."""
    while True:
        try:
            print(f"[{datetime.now()}] Starting scheduled intelligence sync (v2.0)...")
            # In v2.0 we use the Prefect-ready pipeline
            result = commodity_ingestion_pipeline(datetime.now())
            print(f"[{datetime.now()}] Scheduled sync complete. Next sync in 24 hours.")
        except Exception as e:
            print(f"Error in scheduled ingestion: {e}")
        
        # Wait for 24 hours
        await asyncio.sleep(24 * 3600)

async def market_ticker_task():
    """Real-time background task to broadcast minute-by-minute price updates."""
    ncdex = NCDEXConnector()
    mcx = MCXConnector()
    print("Market Ticker Task started. Broadcasting every 60 seconds.")
    
    while True:
        try:
            # Fetch 'ticks' from exchange connectors
            ticks = ncdex.get_live_ticks() + mcx.get_live_ticks()
            
            # Broadcast to all connected WebSocket clients
            await ws_manager.broadcast({
                "type": "TICKER_UPDATE",
                "timestamp": datetime.now().isoformat(),
                "data": ticks
            })
            
            # Use minute-by-minute ticker
            await asyncio.sleep(60) 
        except Exception as e:
            print(f"Ticker Error: {e}")
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    # Start the background tasks
    asyncio.create_task(market_ticker_task())
    
    if settings.PREFECT_ENABLED:
        asyncio.create_task(schedule_ingestion())

@app.websocket("/ws/market-stream")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # We just maintain connection, server pushes updates
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(chatbot_router, prefix=settings.API_V1_STR)
app.include_router(voice_ws_router)

@app.get("/")
def root():
    return {
        "message": "NCEL Intelligence API v2.0 Active",
        "last_sync": datetime.now().isoformat(),
        "status": "Listening for global signals across 7 sources",
        "version": settings.PROJECT_VERSION
    }
