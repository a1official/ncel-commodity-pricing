"""
Data Ingestion Pipeline using Prefect
Orchestrates the complete ETL workflow:
Fetch Data → Store Raw → Normalize → Load to Warehouse → Trigger Forecast
"""

try:
    from prefect import flow, task, get_run_logger
    from prefect.task_runs import task_run
except ImportError:
    # Dummy mocks for prefect
    def task(*args, **kwargs):
        def decorator(func): return func
        return decorator if not args or not callable(args[0]) else args[0]
    
    def flow(*args, **kwargs):
        def decorator(func): return func
        return decorator if not args or not callable(args[0]) else args[0]
    
    def get_run_logger():
        import logging
        return logging.getLogger("dummy_prefect")

from datetime import datetime, timedelta
from typing import List, Dict, Any
import json
import logging
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.ingestion.connectors_enhanced import ConnectorFactory
from app.services.normalization import NormalizationEngine
from app.models import models
from app.services.forecasting_enhanced import MultiSignalForecaster

logger = logging.getLogger(__name__)


@task(name="fetch_data", retries=2, retry_delay_seconds=60)
def fetch_data_task(source_name: str, date_obj: datetime) -> Dict[str, Any]:
    """
    Task: Fetch raw data from a specific source.
    """
    log = get_run_logger()
    log.info(f"Fetching data from {source_name} for {date_obj.date()}")
    
    try:
        connector = ConnectorFactory.get_connector(source_name)
        if not connector:
            log.error(f"Unknown source: {source_name}")
            return {"source": source_name, "status": "failed", "data": []}
        
        raw_data = connector.fetch_data(date_obj)
        log.info(f"Fetched {len(raw_data)} records from {source_name}")
        
        return {
            "source": source_name,
            "status": "success",
            "data": raw_data,
            "count": len(raw_data),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        log.error(f"Error fetching from {source_name}: {e}")
        return {"source": source_name, "status": "failed", "error": str(e), "data": []}


@task(name="store_raw_data")
def store_raw_data_task(fetch_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Task: Store raw data to data lake (in-memory for now, could be S3).
    """
    log = get_run_logger()
    source = fetch_result.get("source")
    
    if fetch_result.get("status") != "success":
        log.warning(f"Skipping storage for failed fetch: {source}")
        return {"source": source, "status": "skipped"}
    
    log.info(f"Storing {fetch_result.get('count', 0)} raw records from {source}")
    
    # In production, this would write to S3 with partitioning
    # For now, we just track that it happened
    return {
        "source": source,
        "status": "stored",
        "record_count": fetch_result.get("count", 0),
        "timestamp": datetime.now().isoformat()
    }


@task(name="normalize_data")
def normalize_data_task(fetch_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Task: Normalize raw data to standard schema.
    """
    log = get_run_logger()
    source = fetch_result.get("source")
    
    if fetch_result.get("status") != "success":
        log.warning(f"Skipping normalization for failed fetch: {source}")
        return {"source": source, "status": "skipped", "data": []}
    
    try:
        connector = ConnectorFactory.get_connector(source)
        if not connector:
            return {"source": source, "status": "failed", "data": []}
        
        raw_data = fetch_result.get("data", [])
        normalized_data = connector.transform_to_standard(raw_data)
        
        log.info(f"Normalized {len(normalized_data)} records from {source}")
        
        return {
            "source": source,
            "status": "success",
            "data": normalized_data,
            "count": len(normalized_data)
        }
    except Exception as e:
        log.error(f"Error normalizing data from {source}: {e}")
        return {"source": source, "status": "failed", "error": str(e), "data": []}


@task(name="load_to_warehouse")
def load_to_warehouse_task(normalized_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Task: Load normalized data into PostgreSQL warehouse.
    """
    log = get_run_logger()
    source = normalized_result.get("source")
    
    if normalized_result.get("status") != "success":
        log.warning(f"Skipping load for failed normalization: {source}")
        return {"source": source, "status": "skipped", "loaded_count": 0}
    
    db = SessionLocal()
    try:
        normalized_data = normalized_result.get("data", [])
        loaded_count = 0
        
        for record in normalized_data:
            try:
                # Get or create commodity
                commodity = db.query(models.Commodity).filter_by(
                    name=record.get("commodity")
                ).first()
                if not commodity:
                    commodity = models.Commodity(
                        name=record.get("commodity"),
                        category=_infer_category(record.get("commodity"))
                    )
                    db.add(commodity)
                    db.flush()
                
                # Get or create variety
                variety = db.query(models.Variety).filter_by(
                    commodity_id=commodity.id,
                    name=record.get("variety")
                ).first()
                if not variety:
                    variety = models.Variety(
                        commodity_id=commodity.id,
                        name=record.get("variety")
                    )
                    db.add(variety)
                    db.flush()
                
                # Get or create state
                state = db.query(models.State).filter_by(
                    name=record.get("state")
                ).first()
                if not state:
                    state = models.State(name=record.get("state"))
                    db.add(state)
                    db.flush()
                
                # Get or create district
                district = db.query(models.District).filter_by(
                    state_id=state.id,
                    name=record.get("district")
                ).first()
                if not district:
                    district = models.District(
                        state_id=state.id,
                        name=record.get("district")
                    )
                    db.add(district)
                    db.flush()
                
                # Get or create market
                market = db.query(models.Market).filter_by(
                    district_id=district.id,
                    name=record.get("market")
                ).first()
                if not market:
                    market = models.Market(
                        district_id=district.id,
                        name=record.get("market")
                    )
                    db.add(market)
                    db.flush()
                
                # Get or create source
                source_obj = db.query(models.Source).filter_by(
                    name=source
                ).first()
                if not source_obj:
                    source_obj = models.Source(
                        name=source,
                        source_type="Government" if source in ["AGMARKNET", "USDA", "FAO"] else "Market"
                    )
                    db.add(source_obj)
                    db.flush()
                
                # Create price record
                price_record = models.PriceRecord(
                    date=record.get("date"),
                    commodity_id=commodity.id,
                    variety_id=variety.id,
                    market_id=market.id,
                    source_id=source_obj.id,
                    min_price=record.get("min_price"),
                    max_price=record.get("max_price"),
                    modal_price=record.get("modal_price"),
                    arrival_quantity=record.get("arrival_quantity", 0),
                    unit=record.get("unit", "Quintal"),
                    normalized_price_per_kg=record.get("normalized_price_per_kg", 0)
                )
                db.add(price_record)
                loaded_count += 1
                
            except Exception as e:
                log.warning(f"Error loading record: {e}")
                continue
        
        db.commit()
        log.info(f"Loaded {loaded_count} records from {source} to warehouse")
        
        return {
            "source": source,
            "status": "success",
            "loaded_count": loaded_count
        }
    except Exception as e:
        db.rollback()
        log.error(f"Error loading to warehouse: {e}")
        return {"source": source, "status": "failed", "error": str(e), "loaded_count": 0}
    finally:
        db.close()


@task(name="trigger_forecasts")
def trigger_forecasts_task(load_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Task: Trigger forecast model for all commodities after data load.
    """
    log = get_run_logger()
    db = SessionLocal()
    
    try:
        forecaster = MultiSignalForecaster(db)
        commodities = db.query(models.Commodity).all()
        
        forecast_count = 0
        for commodity in commodities:
            try:
                forecast = forecaster.get_forecast(commodity.id)
                if "error" not in forecast:
                    forecast_count += 1
                    log.info(f"Generated forecast for {commodity.name}")
            except Exception as e:
                log.warning(f"Error forecasting {commodity.name}: {e}")
        
        log.info(f"Generated {forecast_count} forecasts")
        
        return {
            "status": "success",
            "forecast_count": forecast_count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        log.error(f"Error triggering forecasts: {e}")
        return {"status": "failed", "error": str(e), "forecast_count": 0}
    finally:
        db.close()


@flow(name="commodity_ingestion_pipeline", description="Complete ETL pipeline for commodity prices")
def commodity_ingestion_pipeline(date_obj: datetime = None) -> Dict[str, Any]:
    """
    Main Prefect flow: Orchestrates the complete data ingestion pipeline.
    
    Pipeline steps:
    1. Fetch Data from all sources
    2. Store Raw Data
    3. Normalize Fields
    4. Load to Warehouse
    5. Trigger Forecast Model
    """
    if date_obj is None:
        date_obj = datetime.now()
    
    log = get_run_logger()
    log.info(f"Starting commodity ingestion pipeline for {date_obj.date()}")
    
    # Get all available sources
    sources = ["AGMARKNET", "USDA", "FAO", "APEDA", "MPEDA", "NCDEX", "MCX", "FMPIS"]
    
    # Step 1: Fetch data from all sources
    fetch_results = []
    for source in sources:
        result = fetch_data_task(source, date_obj)
        fetch_results.append(result)
    
    # Step 2: Store raw data
    store_results = []
    for fetch_result in fetch_results:
        result = store_raw_data_task(fetch_result)
        store_results.append(result)
    
    # Step 3: Normalize data
    normalize_results = []
    for fetch_result in fetch_results:
        result = normalize_data_task(fetch_result)
        normalize_results.append(result)
    
    # Step 4: Load to warehouse
    load_results = []
    for normalize_result in normalize_results:
        result = load_to_warehouse_task(normalize_result)
        load_results.append(result)
    
    # Step 5: Invalidate Marine Cache if FMPIS was processed
    if any(r.get("source") == "FMPIS" and r.get("status") == "success" for r in load_results):
        try:
            from app.services.cache import get_cache
            cache = get_cache()
            if cache.enabled:
                cache.invalidate_marine_cache()
                log.info("Marine cache invalidated after successful FMPIS ingestion")
        except Exception as e:
            log.warning(f"Failed to invalidate marine cache: {e}")

    # Step 6: Trigger forecasts
    forecast_result = trigger_forecasts_task(load_results)
    
    # Summary
    total_loaded = sum(r.get("loaded_count", 0) for r in load_results)
    
    summary = {
        "status": "completed",
        "date": date_obj.date().isoformat(),
        "sources_processed": len(sources),
        "total_records_loaded": total_loaded,
        "forecasts_generated": forecast_result.get("forecast_count", 0),
        "timestamp": datetime.now().isoformat()
    }
    
    log.info(f"Pipeline completed: {summary}")
    return summary


@flow(name="daily_ingestion_schedule", description="Daily scheduled ingestion")
def daily_ingestion_schedule():
    """Scheduled daily ingestion flow."""
    return commodity_ingestion_pipeline(datetime.now())


@flow(name="weekly_full_retrain", description="Weekly full model retraining")
def weekly_full_retrain():
    """Weekly full retraining of forecasting models."""
    log = get_run_logger()
    log.info("Starting weekly full model retraining")
    
    # Run full pipeline
    result = commodity_ingestion_pipeline(datetime.now())
    
    log.info(f"Weekly retraining completed: {result}")
    return result


def _infer_category(commodity_name: str) -> str:
    """Infer commodity category from name."""
    commodity_lower = commodity_name.lower()
    
    if any(grain in commodity_lower for grain in ["rice", "wheat", "maize", "millets"]):
        return "Grain"
    elif "index" in commodity_lower:
        return "Intelligence Index"
    elif any(spice in commodity_lower for spice in ["chilli", "turmeric", "cumin", "jeera"]):
        return "Spice"
    elif any(fruit in commodity_lower for fruit in ["banana", "grapes", "pineapple", "tomato"]):
        return "Fruit/Vegetable"
    elif any(marine in commodity_lower for marine in ["shrimp", "mackerel", "tuna", "trout", "fish", "catla", "rohu", "hilsa", "pangas", "tilapia", "mrigal"]):
        return "Marine Products"
    elif any(other in commodity_lower for other in ["cotton", "sugar", "soybean", "groundnut"]):
        return "Cash Crop"
    else:
        return "Other"
