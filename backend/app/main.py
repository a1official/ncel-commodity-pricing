import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints_enhanced import router as api_router
from app.api.v1.chatbot import router as chatbot_router
from app.api.v1.websocket import manager as ws_manager
from app.voice_ai.websocket_gateway import router as voice_ws_router
from app.ingestion.connectors_enhanced import NCDEXConnector, MCXConnector
from app.ingestion.pipeline_orchestrator import commodity_ingestion_pipeline
from app.core.config import settings
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the background tasks
    ticker_task = asyncio.create_task(market_ticker_task())
    mpeda_task = asyncio.create_task(mpeda_sync_task())
    
    ingestion_task = None
    if settings.PREFECT_ENABLED:
        ingestion_task = asyncio.create_task(schedule_ingestion())
        
    yield
    
    # Clean up
    ticker_task.cancel()
    mpeda_task.cancel()
    if ingestion_task:
        ingestion_task.cancel()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
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
            # Run in thread to avoid blocking event loop
            await asyncio.to_thread(commodity_ingestion_pipeline, datetime.now())
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
            await ws_manager.broadcast(
                {
                    "type": "TICKER_UPDATE",
                    "timestamp": datetime.now().isoformat(),
                    "data": ticks,
                }
            )

            # Use minute-by-minute ticker
            await asyncio.sleep(60)
        except Exception as e:
            print(f"Ticker Error: {e}")
            await asyncio.sleep(5)


async def mpeda_sync_task():
    """Background task to download MPEDA data periodically (weekly)."""
    from app.services.mpeda_downloader import download_all_mpeda_data

    while True:
        try:
            print(f"[{datetime.now()}] Downloading MPEDA data...")
            results = download_all_mpeda_data()
            success_count = sum(1 for r in results.values() if r is not None)
            print(
                f"[{datetime.now()}] MPEDA sync complete. Downloaded {success_count}/3 datasets."
            )
        except Exception as e:
            print(f"MPEDA Sync Error: {e}")

        # Wait for 7 days (604800 seconds)
        await asyncio.sleep(7 * 24 * 3600)




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
        "version": settings.PROJECT_VERSION,
    }
