"""
Enhanced API Endpoints for Commodity Intelligence Platform
Provides comprehensive access to prices, forecasts, markets, and analytics.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date, datetime
from ...core.database import get_db
from ...models import models
from ...schemas import schemas
from ...services.forecasting_enhanced import MultiSignalForecaster
from ...ingestion.connectors_enhanced import ConnectorFactory

router = APIRouter()


# ============================================================================
# COMMODITY ENDPOINTS
# ============================================================================

@router.get("/commodities", response_model=List[schemas.Commodity], tags=["Commodities"])
def get_commodities(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Get all commodities with pagination.
    
    Returns list of 21 commodities:
    Rice, Wheat, Maize, Groundnut, Turmeric, Chilli, Cumin, Onion, Tomato,
    Potato, Banana, Grapes, Pineapple, Millets, Shrimp, Mackerel, Tuna, Trout,
    Soybean, Sugar, Cotton
    """
    return db.query(models.Commodity).offset(skip).limit(limit).all()


@router.get("/commodities/search", tags=["Commodities"])
def search_commodities(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
    """
    Search commodities by name with autocomplete support.
    
    Example: /commodities/search?q=rice
    """
    results = db.query(models.Commodity).filter(
        models.Commodity.name.ilike(f"%{q}%")
    ).all()
    
    if not results:
        raise HTTPException(status_code=404, detail="No commodities found")
    
    return {
        "query": q,
        "results": results,
        "count": len(results)
    }


@router.get("/commodities/{commodity_id}", response_model=schemas.Commodity, tags=["Commodities"])
def get_commodity(commodity_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific commodity."""
    commodity = db.query(models.Commodity).filter_by(id=commodity_id).first()
    if not commodity:
        raise HTTPException(status_code=404, detail="Commodity not found")
    return commodity


# ============================================================================
# PRICE ENDPOINTS
# ============================================================================

@router.get("/prices", response_model=List[schemas.PriceRecord], tags=["Prices"])
def get_prices(
    db: Session = Depends(get_db),
    commodity_id: Optional[int] = Query(None),
    commodity_name: Optional[str] = Query(None),
    variety_id: Optional[int] = Query(None),
    variety_name: Optional[str] = Query(None),
    market_id: Optional[int] = Query(None),
    market_name: Optional[str] = Query(None),
    state_name: Optional[str] = Query(None),
    source_id: Optional[int] = Query(None),
    source_name: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000)
):
    """
    Get price records with advanced filtering.
    
    Supports filtering by:
    - Commodity (ID or name)
    - Variety (ID or name)
    - Market (ID or name)
    - State
    - Data Source (ID or name)
    - Date range
    """
    query = db.query(
        models.PriceRecord,
        models.Market.name.label("market_name"),
        models.State.name.label("state_name"),
        models.Source.name.label("source_name"),
        models.Commodity.name.label("commodity_name"),
        models.Variety.name.label("variety_name")
    ).join(models.Market, models.PriceRecord.market_id == models.Market.id)\
     .join(models.District, models.Market.district_id == models.District.id)\
     .join(models.State, models.District.state_id == models.State.id)\
     .join(models.Source, models.PriceRecord.source_id == models.Source.id)\
     .join(models.Commodity, models.PriceRecord.commodity_id == models.Commodity.id)\
     .join(models.Variety, models.PriceRecord.variety_id == models.Variety.id)
    
    # Apply filters
    if commodity_id:
        query = query.filter(models.PriceRecord.commodity_id == commodity_id)
    if commodity_name:
        query = query.filter(models.Commodity.name.ilike(f"%{commodity_name}%"))
    if variety_id:
        query = query.filter(models.PriceRecord.variety_id == variety_id)
    if variety_name:
        query = query.filter(models.Variety.name.ilike(f"%{variety_name}%"))
    if market_id:
        query = query.filter(models.PriceRecord.market_id == market_id)
    if market_name:
        query = query.filter(models.Market.name.ilike(f"%{market_name}%"))
    if state_name:
        query = query.filter(models.State.name.ilike(f"%{state_name}%"))
    if source_id:
        query = query.filter(models.PriceRecord.source_id == source_id)
    if source_name:
        query = query.filter(models.Source.name.ilike(f"%{source_name}%"))
    if start_date:
        query = query.filter(models.PriceRecord.date >= start_date)
    if end_date:
        query = query.filter(models.PriceRecord.date <= end_date)
    
    results = query.order_by(models.PriceRecord.date.desc()).offset(skip).limit(limit).all()
    
    # Flatten results
    final_results = []
    for pr, m_name, s_name, src_name, c_name, v_name in results:
        pr.market_name = m_name
        pr.state_name = s_name
        pr.source_name = src_name
        pr.commodity_name = c_name
        pr.variety_name = v_name
        final_results.append(pr)
    
    return final_results


@router.get("/prices/commodity/{commodity_id}", tags=["Prices"])
def get_commodity_prices(
    commodity_id: int,
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
    source_filter: Optional[str] = Query(None)
):
    """
    Get price history for a specific commodity.
    
    Supports filtering by data source:
    - All Sources (default)
    - AGMARKNET
    - USDA
    - FAO
    - APEDA
    - MPEDA
    - NCDEX
    - MCX
    """
    cutoff_date = datetime.now().date()
    from datetime import timedelta
    start_date = cutoff_date - timedelta(days=days)
    
    query = db.query(models.PriceRecord).filter(
        models.PriceRecord.commodity_id == commodity_id,
        models.PriceRecord.date >= start_date,
        models.PriceRecord.date <= cutoff_date
    )
    
    if source_filter and source_filter != "All Sources":
        source = db.query(models.Source).filter_by(name=source_filter).first()
        if source:
            query = query.filter(models.PriceRecord.source_id == source.id)
    
    prices = query.order_by(models.PriceRecord.date.asc()).all()
    
    if not prices:
        raise HTTPException(status_code=404, detail="No price data found")
    
    return {
        "commodity_id": commodity_id,
        "days": days,
        "source_filter": source_filter or "All Sources",
        "record_count": len(prices),
        "prices": prices
    }


# ============================================================================
# MARKET ENDPOINTS
# ============================================================================

@router.get("/markets", response_model=List[schemas.Market], tags=["Markets"])
def get_markets(
    db: Session = Depends(get_db),
    state_id: Optional[int] = Query(None),
    state_name: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=5000)
):
    """
    Get all markets with optional state filtering.
    Supports all India mandis and variety-wise prices.
    """
    query = db.query(models.Market)
    
    if state_id:
        query = query.join(models.District).filter(
            models.District.state_id == state_id
        )
    elif state_name:
        query = query.join(models.District).join(models.State).filter(
            models.State.name.ilike(f"%{state_name}%")
        )
    
    return query.offset(skip).limit(limit).all()


@router.get("/markets/search", tags=["Markets"])
def search_markets(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
    """Search markets by name."""
    results = db.query(models.Market).filter(
        models.Market.name.ilike(f"%{q}%")
    ).limit(50).all()
    
    return {
        "query": q,
        "results": results,
        "count": len(results)
    }


@router.get("/states", tags=["Markets"])
def get_states(db: Session = Depends(get_db)):
    """Get all states in the system."""
    states = db.query(models.State).all()
    return {"states": states, "count": len(states)}


# ============================================================================
# SOURCE ENDPOINTS
# ============================================================================

@router.get("/sources", tags=["Sources"])
def get_sources(db: Session = Depends(get_db)):
    """
    Get all available data sources.
    
    Sources:
    - AGMARKNET (Government)
    - USDA (Government)
    - FAO (Government)
    - APEDA (Government)
    - MPEDA (Government)
    - NCDEX (Market)
    - MCX (Market)
    - Agriwatch (Private)
    - Volza (Private)
    """
    sources = db.query(models.Source).all()
    return {
        "sources": sources,
        "count": len(sources),
        "available_filters": [
            "All Sources",
            "AGMARKNET",
            "USDA",
            "FAO",
            "APEDA",
            "MPEDA",
            "NCDEX",
            "MCX"
        ]
    }


# ============================================================================
# FORECAST ENDPOINTS
# ============================================================================

@router.get("/forecast/{commodity_id}", tags=["Forecasting"])
def get_forecast(
    commodity_id: int,
    db: Session = Depends(get_db),
    weeks: int = Query(6, ge=1, le=12)
):
    """
    Get multi-week price forecast for a commodity.
    
    Returns:
    - 6-week or 12-week forecast
    - Confidence score (0-100)
    - Trend direction (Bullish/Stable/Bearish)
    - Supply risk indicator (Low/Moderate/High)
    - Confidence intervals for each week
    """
    commodity = db.query(models.Commodity).filter_by(id=commodity_id).first()
    if not commodity:
        raise HTTPException(status_code=404, detail="Commodity not found")
    
    forecaster = MultiSignalForecaster(db)
    forecast = forecaster.get_forecast(commodity_id, weeks)
    
    if "error" in forecast:
        raise HTTPException(status_code=400, detail=forecast["error"])
    
    return forecast


@router.get("/forecast/all", tags=["Forecasting"])
def get_all_forecasts(
    db: Session = Depends(get_db),
    weeks: int = Query(6, ge=1, le=12)
):
    """Get forecasts for all commodities."""
    commodities = db.query(models.Commodity).all()
    forecaster = MultiSignalForecaster(db)
    
    forecasts = []
    for commodity in commodities:
        try:
            forecast = forecaster.get_forecast(commodity.id, weeks)
            if "error" not in forecast:
                forecast["commodity_name"] = commodity.name
                forecasts.append(forecast)
        except Exception as e:
            continue
    
    return {
        "forecast_count": len(forecasts),
        "forecasts": forecasts,
        "weeks": weeks
    }


# ============================================================================
# MARINE ENDPOINTS
# ============================================================================

@router.get("/marine/states", tags=["Marine"])
def get_marine_states(db: Session = Depends(get_db)):
    """Get all states that have marine commodity data."""
    from sqlalchemy import distinct
    
    try:
        # Import cache service
        from app.services.cache import get_cache
        cache = get_cache()
        
        # Try to get from cache first
        if cache.enabled:
            cached_states = cache.get_marine_states()
            if cached_states:
                return cached_states
    except Exception as e:
        # If cache fails, continue with database query
        pass
    
    # Query database
    states = db.query(distinct(models.State.name))\
        .join(models.District, models.State.id == models.District.state_id)\
        .join(models.Market, models.District.id == models.Market.district_id)\
        .join(models.PriceRecord, models.Market.id == models.PriceRecord.market_id)\
        .join(models.Commodity, models.PriceRecord.commodity_id == models.Commodity.id)\
        .join(models.Source, models.PriceRecord.source_id == models.Source.id)\
        .filter(models.Commodity.category == "Marine Products")\
        .filter(models.Source.name == "FMPIS")\
        .order_by(models.State.name)\
        .all()
    
    result = [state[0] for state in states]
    
    # Try to cache the result
    try:
        from app.services.cache import get_cache
        cache = get_cache()
        if cache.enabled:
            cache.set_marine_states(result)
    except Exception as e:
        # If cache fails, continue without caching
        pass
    
    return result

@router.get("/marine/summary", tags=["Marine"])
def get_marine_summary(db: Session = Depends(get_db)):
    """Get marine commodity summary with latest prices by state."""
    from sqlalchemy import func, desc
    
    try:
        # Import cache service
        from app.services.cache import get_cache
        cache = get_cache()
        
        # Try to get from cache first
        if cache.enabled:
            cached_summary = cache.get_marine_summary()
            if cached_summary:
                return cached_summary
    except Exception as e:
        # If cache fails, continue with database query
        pass
    
    try:
        # Simplified query - get recent marine price records
        results = db.query(
            models.Commodity.name.label("commodity_name"),
            models.State.name.label("state_name"),
            models.PriceRecord.modal_price,
            models.PriceRecord.date
        ).join(models.Market, models.PriceRecord.market_id == models.Market.id)\
         .join(models.District, models.Market.district_id == models.District.id)\
         .join(models.State, models.District.state_id == models.State.id)\
         .join(models.Commodity, models.PriceRecord.commodity_id == models.Commodity.id)\
         .join(models.Source, models.PriceRecord.source_id == models.Source.id)\
         .filter(models.Commodity.category == "Marine Products")\
         .filter(models.Source.name == "FMPIS")\
         .order_by(desc(models.PriceRecord.date))\
         .limit(1000)\
         .all()
        
        result = [
            {
                "commodity_name": r.commodity_name,
                "state_name": r.state_name,
                "modal_price": float(r.modal_price),
                "date": r.date.isoformat(),
                "record_count": 1
            }
            for r in results
        ]
        
        # Try to cache the result
        try:
            from app.services.cache import get_cache
            cache = get_cache()
            if cache.enabled:
                cache.set_marine_summary(result)
        except Exception as e:
            # If cache fails, continue without caching
            pass
        
        return result
        
    except Exception as e:
        # If query fails, return empty list
        return []


# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================

@router.get("/analytics/daily-average", tags=["Analytics"])
@router.get("/insights/daily-average", tags=["Analytics"])
def get_daily_average(
    commodity_id: int,
    db: Session = Depends(get_db)
):
    """Get daily average price for a commodity."""
    avg_price = db.query(func.avg(models.PriceRecord.modal_price))\
        .filter(models.PriceRecord.commodity_id == commodity_id)\
        .scalar()
    
    avg_normalized = db.query(func.avg(models.PriceRecord.normalized_price_per_kg))\
        .filter(models.PriceRecord.commodity_id == commodity_id)\
        .scalar()
    
    if avg_price is None:
        raise HTTPException(status_code=404, detail="No data found")
    
    return {
        "commodity_id": commodity_id,
        "average_price": float(avg_price),
        "average_price_per_kg": float(avg_normalized or (avg_price / 100)),
        "unit": "INR"
    }


@router.get("/analytics/price-range", tags=["Analytics"])
def get_price_range(
    commodity_id: int,
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
):
    """Get min/max/avg prices for a commodity over a period."""
    from datetime import timedelta
    cutoff_date = datetime.now().date()
    start_date = cutoff_date - timedelta(days=days)
    
    records = db.query(models.PriceRecord).filter(
        models.PriceRecord.commodity_id == commodity_id,
        models.PriceRecord.date >= start_date
    ).all()
    
    if not records:
        raise HTTPException(status_code=404, detail="No data found")
    
    prices = [float(r.modal_price) for r in records]
    
    return {
        "commodity_id": commodity_id,
        "period_days": days,
        "min_price": min(prices),
        "max_price": max(prices),
        "avg_price": sum(prices) / len(prices),
        "record_count": len(prices)
    }


@router.get("/analytics/source-comparison", tags=["Analytics"])
def get_source_comparison(
    commodity_id: int,
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
):
    """Compare prices across different data sources."""
    from datetime import timedelta
    cutoff_date = datetime.now().date()
    start_date = cutoff_date - timedelta(days=days)
    
    results = db.query(
        models.Source.name,
        func.avg(models.PriceRecord.modal_price).label("avg_price"),
        func.min(models.PriceRecord.modal_price).label("min_price"),
        func.max(models.PriceRecord.modal_price).label("max_price"),
        func.count(models.PriceRecord.id).label("record_count")
    ).join(models.Source).filter(
        models.PriceRecord.commodity_id == commodity_id,
        models.PriceRecord.date >= start_date
    ).group_by(models.Source.name).all()
    
    if not results:
        raise HTTPException(status_code=404, detail="No data found")
    
    comparison = []
    for source_name, avg_price, min_price, max_price, count in results:
        comparison.append({
            "source": source_name,
            "avg_price": float(avg_price) if avg_price else 0,
            "min_price": float(min_price) if min_price else 0,
            "max_price": float(max_price) if max_price else 0,
            "record_count": count
        })
    
    return {
        "commodity_id": commodity_id,
        "period_days": days,
        "sources": comparison
    }


# ============================================================================
# INGESTION ENDPOINTS
# ============================================================================

from fastapi import BackgroundTasks

@router.post("/ingest", tags=["Ingestion"])
async def trigger_ingestion(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Trigger background data ingestion cycle.
    
    Returns immediately and runs the ETL pipeline in the background:
    Fetch Data → Store Raw → Normalize → Load to Warehouse → Trigger Forecast
    """
    from ...ingestion.pipeline_orchestrator import commodity_ingestion_pipeline
    
    # We trigger the pipeline in the background so the UI doesn't hang
    # Prefect flows are already designed to be robust under this pattern
    background_tasks.add_task(commodity_ingestion_pipeline, datetime.now())
    
    return {
        "status": "success",
        "message": "Ingestion cycle started in background",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/ingest/{source_name}", tags=["Ingestion"])
def trigger_source_ingestion(
    source_name: str,
    db: Session = Depends(get_db)
):
    """Trigger ingestion for a specific source."""
    connector = ConnectorFactory.get_connector(source_name)
    if not connector:
        raise HTTPException(status_code=404, detail=f"Unknown source: {source_name}")
    
    try:
        raw_data = connector.fetch_data(datetime.now())
        normalized_data = connector.transform_to_standard(raw_data)
        
        return {
            "status": "success",
            "source": source_name,
            "raw_records": len(raw_data),
            "normalized_records": len(normalized_data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health", tags=["System"])
def health_check():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "features": [
            "Multi-source data integration",
            "Ensemble forecasting (LSTM + XGBoost)",
            "Prefect pipeline orchestration",
            "21 commodities support",
            "Source filtering",
            "Advanced analytics"
        ]
    }
