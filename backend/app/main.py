import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.v1.endpoints import router as api_router
from .core.config import settings
from .ingestion.orchestrator import IngestionOrchestrator
from datetime import datetime

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def schedule_ingestion():
    """Background task to run ingestion every 24 hours."""
    while True:
        try:
            print(f"[{datetime.now()}] Starting scheduled intelligence sync...")
            orchestrator = IngestionOrchestrator()
            orchestrator.run_daily_ingestion()
            print(f"[{datetime.now()}] Scheduled sync complete. Next sync in 24 hours.")
        except Exception as e:
            print(f"Error in scheduled ingestion: {e}")
        
        # Wait for 24 hours
        await asyncio.sleep(24 * 3600)

@app.on_event("startup")
async def startup_event():
    # Start the background task
    asyncio.create_task(schedule_ingestion())

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "message": "NCEL Intelligence API Active",
        "last_sync": datetime.now().isoformat(),
        "status": "Listening for global signals"
    }
