import asyncio
from datetime import datetime
from app.ingestion.connectors_enhanced import MarineConnector
from app.core.database import SessionLocal
from app.models import models

def test_fmpis_ingestion():
    connector = MarineConnector()
    print("Fetching FMPIS data...")
    raw_data = connector.fetch_data(datetime.now())
    print(f"Fetched {len(raw_data)} raw records.")
    
    if not raw_data:
        print("No data fetched. API might be down or session issue.")
        return

    print("Normalizing data...")
    normalized = connector.transform_to_standard(raw_data)
    print(f"Normalized {len(normalized)} records.")

    db = SessionLocal()
    try:
        from app.ingestion.pipeline_orchestrator import load_to_warehouse_task
        # We wrap it in the task result format expected by load_to_warehouse_task
        normalized_result = {
            "source": "FMPIS",
            "status": "success",
            "data": normalized,
            "count": len(normalized)
        }
        print("Loading to warehouse...")
        result = load_to_warehouse_task(normalized_result)
        print(f"Load result: {result}")
    finally:
        db.close()

if __name__ == "__main__":
    test_fmpis_ingestion()
