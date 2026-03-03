from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from ...core.database import get_db
from ...models import models
from ...schemas import schemas

router = APIRouter()

@router.get("/commodities", response_model=List[schemas.Commodity])
def get_commodities(db: Session = Depends(get_db)):
    return db.query(models.Commodity).all()

@router.get("/markets", response_model=List[schemas.Market])
def get_markets(db: Session = Depends(get_db)):
    return db.query(models.Market).all()

@router.get("/prices", response_model=List[schemas.PriceRecord])
def get_prices(
    db: Session = Depends(get_db),
    commodity_id: Optional[int] = Query(None),
    variety_id: Optional[int] = Query(None),
    market_id: Optional[int] = Query(None),
    commodity_name: Optional[str] = Query(None),
    variety_name: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
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
     
    if commodity_id:
        query = query.filter(models.PriceRecord.commodity_id == commodity_id)
    if variety_id:
        query = query.filter(models.PriceRecord.variety_id == variety_id)
    if market_id:
        query = query.filter(models.PriceRecord.market_id == market_id)
    if commodity_name:
        query = query.filter(models.Commodity.name.ilike(f"%{commodity_name}%"))
    if variety_name:
        query = query.filter(models.Variety.name.ilike(f"%{variety_name}%"))
    if start_date:
        query = query.filter(models.PriceRecord.date >= start_date)
    if end_date:
        query = query.filter(models.PriceRecord.date <= end_date)
    
    results = query.order_by(models.PriceRecord.date.desc()).limit(200).all()
    
    # Flatten results because query returns [(PriceRecord, market_name, state_name, source_name)]
    final_results = []
    for pr, m_name, s_name, src_name, c_name, v_name in results:
        pr.market_name = m_name
        pr.state_name = s_name
        pr.source_name = src_name
        pr.commodity_name = c_name
        pr.variety_name = v_name
        final_results.append(pr)
        
    return final_results

@router.get("/insights/daily-average")
def get_daily_average(commodity_id: int, db: Session = Depends(get_db)):
    # This would be a more complex aggregation in a real app
    from sqlalchemy import func
    avg_price = db.query(func.avg(models.PriceRecord.normalized_price_per_kg))\
        .filter(models.PriceRecord.commodity_id == commodity_id)\
        .scalar()
    return {"commodity_id": commodity_id, "average_price_per_kg": float(avg_price or 0)}

@router.post("/ingest")
def trigger_ingestion():
    from ...ingestion.orchestrator import IngestionOrchestrator
    try:
        orchestrator = IngestionOrchestrator()
        orchestrator.run_daily_ingestion()
        return {"status": "success", "message": "Intelligence discovery cycle complete."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/forecast/{commodity_id}")
def get_hybrid_forecast(commodity_id: int, db: Session = Depends(get_db)):
    from ...services.forecasting import HybridLSTMForecaster
    forecaster = HybridLSTMForecaster(db)
    result = forecaster.get_forecast(commodity_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
