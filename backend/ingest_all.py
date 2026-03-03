import os
import sys
from datetime import datetime

# Set Python path to include ncel folder
sys.path.append(os.getcwd())

from app.ingestion.orchestrator import IngestionOrchestrator

if __name__ == "__main__":
    print("Initiating full multi-source intelligence ingestion...")
    orchestrator = IngestionOrchestrator()
    # Ingest for today
    orchestrator.run_daily_ingestion(datetime.now())
    print("Ingestion flow completed for all 11 active connectors.")
