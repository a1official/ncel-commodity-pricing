"""
Enhanced API Endpoints for Commodity Intelligence Platform
Provides comprehensive access to prices, forecasts, markets, and analytics.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from sqlalchemy.exc import OperationalError
from typing import List, Optional
from datetime import date, datetime, timedelta
import sqlite3
import logging
import traceback
from pathlib import Path
from decimal import Decimal
from io import BytesIO

import pandas as pd

from app.core.database import get_db
from app.models import models
from app.schemas import schemas
from app.services.forecasting_enhanced import MultiSignalForecaster
from app.services.daily_price_sync import DailyAgmarknetSyncService
from app.services.analytics_dashboard import AnalyticsDashboardService
from app.services.maize_forecasting import MaizeMonteCarloForecaster
from app.services.maize_ml_forecasting import MaizeFeatureForecaster
from app.services.rice_forecasting import RiceMonteCarloForecaster
from app.services.rice_ml_forecasting import RiceFeatureForecaster
from app.services.wheat_ml_forecasting import WheatFeatureForecaster
from app.services.wheat_forecasting import WheatMonteCarloForecaster
from app.ingestion.connectors_enhanced import ConnectorFactory
from app.services.cache import get_cache

router = APIRouter()
logger = logging.getLogger(__name__)
SUPPLY_DEMAND_DB_PATH = Path(__file__).resolve().parents[3] / "data" / "supply_demand_analytics.db"


def _as_float(value) -> float:
    return float(value) if value is not None else 0.0


def _apply_price_filters(query, *, commodity_id=None, commodity_name=None, variety_id=None, variety_name=None,
                         market_id=None, market_name=None, state_name=None, source_id=None, source_name=None,
                         category=None, start_date=None, end_date=None):
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
    if category:
        query = query.filter(models.Commodity.category.ilike(f"%{category}%"))
    return query


def _price_joined_query(db: Session):
    return (
        db.query(
            models.PriceRecord,
            models.Market.name.label("market_name"),
            models.State.name.label("state_name"),
            models.Source.name.label("source_name"),
            models.Commodity.name.label("commodity_name"),
            models.Variety.name.label("variety_name"),
        )
        .join(models.Market, models.PriceRecord.market_id == models.Market.id)
        .join(models.District, models.Market.district_id == models.District.id)
        .join(models.State, models.District.state_id == models.State.id)
        .join(models.Source, models.PriceRecord.source_id == models.Source.id)
        .join(models.Commodity, models.PriceRecord.commodity_id == models.Commodity.id)
        .join(models.Variety, models.PriceRecord.variety_id == models.Variety.id)
    )


def _flatten_price_rows(rows):
    final_results = []
    for pr, m_name, s_name, src_name, c_name, v_name in rows:
        pr.market_name = m_name
        pr.state_name = s_name
        pr.source_name = src_name
        pr.commodity_name = c_name
        pr.variety_name = v_name
        final_results.append(pr)
    return final_results


def _normalize_price_per_kg(price: Decimal, unit: str) -> Decimal:
    normalized_unit = (unit or "").strip().upper()
    if normalized_unit in {"KG", "KILOGRAM"}:
        return price
    if normalized_unit in {"QUINTAL", "QTL"}:
        return price / Decimal("100")
    if normalized_unit in {"TON", "TONNE", "MT"}:
        return price / Decimal("1000")
    return price


def _get_or_create_ncel_source(db: Session):
    source = db.query(models.Source).filter(func.lower(models.Source.name) == "ncel").first()
    if source is None:
        source = models.Source(name="NCEL", source_type="Manual")
        db.add(source)
        db.flush()
    return source


def _resolve_variety_for_manual(db: Session, commodity_id: int, market_id: int):
    variety = (
        db.query(models.Variety)
        .join(models.PriceRecord, models.PriceRecord.variety_id == models.Variety.id)
        .filter(
            models.PriceRecord.commodity_id == commodity_id,
            models.PriceRecord.market_id == market_id,
        )
        .order_by(models.PriceRecord.date.desc())
        .first()
    )
    if variety is None:
        variety = (
            db.query(models.Variety)
            .filter(models.Variety.commodity_id == commodity_id)
            .order_by(models.Variety.id.asc())
            .first()
    )
    return variety


def _resolve_market_for_bulk_row(
    db: Session,
    row: pd.Series,
    dataframe: pd.DataFrame,
):
    if "market_id" in dataframe.columns and str(row["market_id"]).strip() != "":
        return int(row["market_id"])

    if "market_name" in dataframe.columns and str(row["market_name"]).strip() != "":
        market_name = str(row["market_name"]).strip()
        market = (
            db.query(models.Market)
            .filter(func.lower(models.Market.name) == market_name.lower())
            .first()
        )
        if market is not None:
            return int(market.id)
        raise ValueError(f"Unknown market_name '{market_name}'")

    raise ValueError("Either market_id or market_name is required")


def _upsert_ncel_price_record(
    db: Session,
    *,
    commodity_id: int,
    market_id: int,
    record_date,
    modal_price: Decimal,
    min_price: Decimal | None,
    max_price: Decimal | None,
    arrival_quantity: Decimal,
    unit: str,
):
    commodity = db.query(models.Commodity).filter(models.Commodity.id == commodity_id).first()
    if not commodity:
        raise HTTPException(status_code=404, detail="Commodity not found")

    market = db.query(models.Market).filter(models.Market.id == market_id).first()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    source = _get_or_create_ncel_source(db)
    variety = _resolve_variety_for_manual(db, commodity_id, market_id)
    if variety is None:
        raise HTTPException(status_code=400, detail="No variety is mapped to this commodity yet")

    resolved_min_price = Decimal(min_price) if min_price is not None else Decimal(modal_price)
    resolved_max_price = Decimal(max_price) if max_price is not None else Decimal(modal_price)
    normalized_price = _normalize_price_per_kg(Decimal(modal_price), unit)

    record = (
        db.query(models.PriceRecord)
        .filter(
            models.PriceRecord.date == record_date,
            models.PriceRecord.commodity_id == commodity_id,
            models.PriceRecord.market_id == market_id,
            models.PriceRecord.source_id == source.id,
        )
        .first()
    )

    created = record is None
    if created:
        record = models.PriceRecord(
            date=record_date,
            commodity_id=commodity_id,
            variety_id=variety.id,
            market_id=market_id,
            source_id=source.id,
            min_price=resolved_min_price,
            max_price=resolved_max_price,
            modal_price=Decimal(modal_price),
            arrival_quantity=Decimal(arrival_quantity),
            unit=unit,
            normalized_price_per_kg=normalized_price,
        )
        db.add(record)
    else:
        record.variety_id = variety.id
        record.min_price = resolved_min_price
        record.max_price = resolved_max_price
        record.modal_price = Decimal(modal_price)
        record.arrival_quantity = Decimal(arrival_quantity)
        record.unit = unit
        record.normalized_price_per_kg = normalized_price

    return record, created


def _fetch_supply_demand_rows():
    if not SUPPLY_DEMAND_DB_PATH.exists():
        raise HTTPException(status_code=404, detail="Supply-demand analytics database not found")
    with sqlite3.connect(str(SUPPLY_DEMAND_DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT s.*
            FROM supply_demand_signals s
            JOIN (
                SELECT crop, frequency, MAX(signal_date) AS max_signal_date
                FROM supply_demand_signals
                GROUP BY crop, frequency
            ) latest
              ON latest.crop = s.crop
             AND latest.frequency = s.frequency
             AND latest.max_signal_date = s.signal_date
            ORDER BY s.crop
            """
        ).fetchall()
    return [dict(row) for row in rows]


def _fetch_supply_demand_delta_history(crop: str | None = None):
    if not SUPPLY_DEMAND_DB_PATH.exists():
        raise HTTPException(status_code=404, detail="Supply-demand analytics database not found")
    with sqlite3.connect(str(SUPPLY_DEMAND_DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        query = """
            SELECT *
            FROM supply_demand_delta_history
        """
        params = []
        if crop:
            query += " WHERE LOWER(crop) = LOWER(?)"
            params.append(crop)
        query += """
            ORDER BY crop,
                CASE WHEN marketing_year = 'Current Snapshot' THEN 9999 ELSE CAST(SUBSTR(marketing_year, 1, 4) AS INTEGER) END
        """
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]

# ============================================================================
# COMMODITY ENDPOINTS
# ============================================================================


@router.get(
    "/commodities", response_model=List[schemas.Commodity], tags=["Commodities"]
)
def get_commodities(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """Get all commodities with pagination."""
    return db.query(models.Commodity).offset(skip).limit(limit).all()


@router.get("/commodities/search", tags=["Commodities"])
def search_commodities(
    q: str = Query(..., min_length=1), db: Session = Depends(get_db)
):
    """Search commodities by name with autocomplete support."""
    results = (
        db.query(models.Commodity).filter(models.Commodity.name.ilike(f"%{q}%")).all()
    )
    if not results:
        raise HTTPException(status_code=404, detail="No commodities found")
    return {"query": q, "results": results, "count": len(results)}


@router.get("/commodities/overview", tags=["Commodities"])
def get_commodities_overview(
    db: Session = Depends(get_db),
    limit: int = Query(200, ge=1, le=500),
):
    """Return commodity master data with latest AGMARKNET price snapshot when available."""
    commodities = db.query(models.Commodity).order_by(models.Commodity.name.asc()).limit(limit).all()

    latest_dates_subquery = (
        db.query(
            models.PriceRecord.commodity_id.label("commodity_id"),
            func.max(models.PriceRecord.date).label("latest_date"),
        )
        .join(models.Source, models.PriceRecord.source_id == models.Source.id)
        .filter(models.Source.name.ilike("AGMARKNET"))
        .group_by(models.PriceRecord.commodity_id)
        .subquery()
    )

    latest_price_rows = (
        db.query(
            models.PriceRecord.commodity_id.label("commodity_id"),
            models.PriceRecord.date.label("date"),
            models.PriceRecord.modal_price.label("modal_price"),
            models.PriceRecord.arrival_quantity.label("arrival_quantity"),
            models.PriceRecord.unit.label("unit"),
            models.Market.name.label("market_name"),
            models.State.name.label("state_name"),
        )
        .join(models.Source, models.PriceRecord.source_id == models.Source.id)
        .join(models.Market, models.PriceRecord.market_id == models.Market.id)
        .join(models.District, models.Market.district_id == models.District.id)
        .join(models.State, models.District.state_id == models.State.id)
        .join(
            latest_dates_subquery,
            (models.PriceRecord.commodity_id == latest_dates_subquery.c.commodity_id)
            & (models.PriceRecord.date == latest_dates_subquery.c.latest_date),
        )
        .filter(models.Source.name.ilike("AGMARKNET"))
        .all()
    )

    latest_by_commodity = {}
    for row in latest_price_rows:
        current = latest_by_commodity.get(row.commodity_id)
        if current is None or _as_float(row.modal_price) > _as_float(current["modal_price"]):
            latest_by_commodity[row.commodity_id] = {
                "date": row.date.isoformat() if row.date else None,
                "modal_price": _as_float(row.modal_price),
                "arrival_quantity": _as_float(row.arrival_quantity),
                "unit": row.unit,
                "market_name": row.market_name,
                "state_name": row.state_name,
                "source_name": "AGMARKNET",
            }

    return [
        {
            "id": commodity.id,
            "name": commodity.name,
            "category": commodity.category,
            "latest_price": latest_by_commodity.get(commodity.id),
        }
        for commodity in commodities
    ]


@router.get(
    "/commodities/{commodity_id}",
    response_model=schemas.Commodity,
    tags=["Commodities"],
)
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
    category: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=300),
):
    """Get price records with advanced filtering."""
    query = _apply_price_filters(
        _price_joined_query(db),
        commodity_id=commodity_id,
        commodity_name=commodity_name,
        variety_id=variety_id,
        variety_name=variety_name,
        market_id=market_id,
        market_name=market_name,
        state_name=state_name,
        source_id=source_id,
        source_name=source_name,
        category=category,
        start_date=start_date,
        end_date=end_date,
    )

    results = (
        query.order_by(models.PriceRecord.date.desc()).offset(skip).limit(limit).all()
    )
    return _flatten_price_rows(results)


@router.post(
    "/prices/manual",
    response_model=schemas.ManualPriceUpdateResponse,
    tags=["Prices"],
)
def upsert_manual_price(
    payload: schemas.ManualPriceUpdateRequest,
    db: Session = Depends(get_db),
):
    """Create or update a manual NCEL price record for a commodity/date/market."""
    record, created = _upsert_ncel_price_record(
        db,
        commodity_id=payload.commodity_id,
        market_id=payload.market_id,
        record_date=payload.date,
        modal_price=Decimal(payload.modal_price),
        min_price=payload.min_price,
        max_price=payload.max_price,
        arrival_quantity=Decimal(payload.arrival_quantity),
        unit=payload.unit,
    )

    db.commit()

    row = (
        _price_joined_query(db)
        .filter(models.PriceRecord.id == record.id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=500, detail="Saved record could not be reloaded")

    return {
        "status": "success",
        "message": "Manual NCEL price added" if created else "Manual NCEL price updated",
        "record": _flatten_price_rows([row])[0],
    }


@router.delete(
    "/prices/manual/{record_id}",
    response_model=schemas.ManualPriceDeleteResponse,
    tags=["Prices"],
)
def delete_manual_price(
    record_id: str,
    db: Session = Depends(get_db),
):
    """Delete only manual NCEL records."""
    row = (
        _price_joined_query(db)
        .filter(models.PriceRecord.id == record_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Price record not found")

    if str(row.source_name or "").upper() != "NCEL":
        raise HTTPException(status_code=403, detail="Only NCEL manual records can be deleted")

    record = db.query(models.PriceRecord).filter(models.PriceRecord.id == record_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Price record not found")

    db.delete(record)
    db.commit()

    return {
        "status": "success",
        "message": "Manual NCEL price deleted",
        "record_id": record_id,
    }


@router.post("/prices/manual/bulk", tags=["Prices"])
async def bulk_upload_manual_prices(
    commodity_id: int = Query(..., ge=1),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload CSV/XLSX rows and save them as NCEL manual prices for one commodity."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="A file is required")

    filename = file.filename.lower()
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        if filename.endswith(".csv"):
            dataframe = pd.read_csv(BytesIO(file_bytes))
        elif filename.endswith(".xlsx") or filename.endswith(".xls"):
            dataframe = pd.read_excel(BytesIO(file_bytes))
        else:
            raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse uploaded sheet: {exc}") from exc

    required_columns = {"date", "modal_price"}
    missing_columns = [column for column in required_columns if column not in dataframe.columns]
    if missing_columns:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {', '.join(missing_columns)}",
        )
    if "market_id" not in dataframe.columns and "market_name" not in dataframe.columns:
        raise HTTPException(
            status_code=400,
            detail="Sheet must include either market_id or market_name",
        )

    created_count = 0
    updated_count = 0
    errors = []

    for index, row in dataframe.fillna("").iterrows():
        try:
            record_date = pd.to_datetime(row["date"]).date()
            market_id = _resolve_market_for_bulk_row(db, row, dataframe)
            modal_price = Decimal(str(row["modal_price"]))
            min_price = Decimal(str(row["min_price"])) if "min_price" in dataframe.columns and str(row["min_price"]).strip() != "" else None
            max_price = Decimal(str(row["max_price"])) if "max_price" in dataframe.columns and str(row["max_price"]).strip() != "" else None
            arrival_quantity = Decimal(str(row["arrival_quantity"])) if "arrival_quantity" in dataframe.columns and str(row["arrival_quantity"]).strip() != "" else Decimal("0")
            unit = str(row["unit"]).strip() if "unit" in dataframe.columns and str(row["unit"]).strip() != "" else "QUINTAL"

            _, created = _upsert_ncel_price_record(
                db,
                commodity_id=commodity_id,
                market_id=market_id,
                record_date=record_date,
                modal_price=modal_price,
                min_price=min_price,
                max_price=max_price,
                arrival_quantity=arrival_quantity,
                unit=unit,
            )
            if created:
                created_count += 1
            else:
                updated_count += 1
        except Exception as exc:
            errors.append({"row": int(index) + 2, "error": str(exc)})

    db.commit()

    return {
        "status": "success",
        "commodity_id": commodity_id,
        "created": created_count,
        "updated": updated_count,
        "failed": len(errors),
        "errors": errors[:20],
        "message": f"Processed {created_count + updated_count} row(s) for NCEL upload",
    }


@router.get("/prices/page", tags=["Prices"])
def get_prices_page(
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
    category: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=300),
):
    """Strictly paginated records endpoint with metadata for large UI tables."""
    filtered_ids = _apply_price_filters(
        db.query(models.PriceRecord.id),
        commodity_id=commodity_id,
        commodity_name=commodity_name,
        variety_id=variety_id,
        variety_name=variety_name,
        market_id=market_id,
        market_name=market_name,
        state_name=state_name,
        source_id=source_id,
        source_name=source_name,
        category=category,
        start_date=start_date,
        end_date=end_date,
    )
    total = filtered_ids.count()

    records_query = _apply_price_filters(
        _price_joined_query(db),
        commodity_id=commodity_id,
        commodity_name=commodity_name,
        variety_id=variety_id,
        variety_name=variety_name,
        market_id=market_id,
        market_name=market_name,
        state_name=state_name,
        source_id=source_id,
        source_name=source_name,
        category=category,
        start_date=start_date,
        end_date=end_date,
    )
    rows = records_query.order_by(models.PriceRecord.date.desc()).offset(skip).limit(limit).all()
    items = _flatten_price_rows(rows)
    returned = len(items)

    return {
        "items": items,
        "pagination": {
            "skip": skip,
            "limit": limit,
            "returned": returned,
            "total": total,
            "has_more": (skip + returned) < total,
        },
    }


@router.get("/prices/summary", tags=["Prices"])
def get_prices_summary(
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
    category: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """Lightweight KPI endpoint to avoid shipping raw rows for top cards."""
    base = _apply_price_filters(
        db.query(
            func.count(models.PriceRecord.id).label("record_count"),
            func.avg(models.PriceRecord.normalized_price_per_kg).label("avg_price_per_kg"),
            func.sum(models.PriceRecord.arrival_quantity).label("total_arrival_quantity"),
            func.max(models.PriceRecord.date).label("latest_date"),
        )
        .select_from(models.PriceRecord)
        .join(models.Market, models.PriceRecord.market_id == models.Market.id)
        .join(models.District, models.Market.district_id == models.District.id)
        .join(models.State, models.District.state_id == models.State.id)
        .join(models.Source, models.PriceRecord.source_id == models.Source.id)
        .join(models.Commodity, models.PriceRecord.commodity_id == models.Commodity.id)
        .join(models.Variety, models.PriceRecord.variety_id == models.Variety.id),
        commodity_id=commodity_id,
        commodity_name=commodity_name,
        variety_id=variety_id,
        variety_name=variety_name,
        market_id=market_id,
        market_name=market_name,
        state_name=state_name,
        source_id=source_id,
        source_name=source_name,
        category=category,
        start_date=start_date,
        end_date=end_date,
    )
    aggregate = base.one()

    distinct_markets_query = _apply_price_filters(
        db.query(func.count(distinct(models.PriceRecord.market_id)))
        .select_from(models.PriceRecord)
        .join(models.Market, models.PriceRecord.market_id == models.Market.id)
        .join(models.District, models.Market.district_id == models.District.id)
        .join(models.State, models.District.state_id == models.State.id)
        .join(models.Source, models.PriceRecord.source_id == models.Source.id)
        .join(models.Commodity, models.PriceRecord.commodity_id == models.Commodity.id)
        .join(models.Variety, models.PriceRecord.variety_id == models.Variety.id),
        commodity_id=commodity_id,
        commodity_name=commodity_name,
        variety_id=variety_id,
        variety_name=variety_name,
        market_id=market_id,
        market_name=market_name,
        state_name=state_name,
        source_id=source_id,
        source_name=source_name,
        category=category,
        start_date=start_date,
        end_date=end_date,
    )
    unique_markets = int(distinct_markets_query.scalar() or 0)

    latest_date = aggregate.latest_date
    latest_avg_price = 0.0
    seven_day_change_pct = 0.0
    if latest_date:
        latest_avg_price = _as_float(
            _apply_price_filters(
                db.query(func.avg(models.PriceRecord.normalized_price_per_kg))
                .select_from(models.PriceRecord)
                .join(models.Market, models.PriceRecord.market_id == models.Market.id)
                .join(models.District, models.Market.district_id == models.District.id)
                .join(models.State, models.District.state_id == models.State.id)
                .join(models.Source, models.PriceRecord.source_id == models.Source.id)
                .join(models.Commodity, models.PriceRecord.commodity_id == models.Commodity.id)
                .join(models.Variety, models.PriceRecord.variety_id == models.Variety.id)
                .filter(models.PriceRecord.date == latest_date),
                commodity_id=commodity_id,
                commodity_name=commodity_name,
                variety_id=variety_id,
                variety_name=variety_name,
                market_id=market_id,
                market_name=market_name,
                state_name=state_name,
                source_id=source_id,
                source_name=source_name,
                category=category,
                start_date=start_date,
                end_date=end_date,
            ).scalar()
        )
        past_cutoff = latest_date - timedelta(days=7)
        prior_avg = _as_float(
            _apply_price_filters(
                db.query(func.avg(models.PriceRecord.normalized_price_per_kg))
                .select_from(models.PriceRecord)
                .join(models.Market, models.PriceRecord.market_id == models.Market.id)
                .join(models.District, models.Market.district_id == models.District.id)
                .join(models.State, models.District.state_id == models.State.id)
                .join(models.Source, models.PriceRecord.source_id == models.Source.id)
                .join(models.Commodity, models.PriceRecord.commodity_id == models.Commodity.id)
                .join(models.Variety, models.PriceRecord.variety_id == models.Variety.id)
                .filter(models.PriceRecord.date < latest_date, models.PriceRecord.date >= past_cutoff),
                commodity_id=commodity_id,
                commodity_name=commodity_name,
                variety_id=variety_id,
                variety_name=variety_name,
                market_id=market_id,
                market_name=market_name,
                state_name=state_name,
                source_id=source_id,
                source_name=source_name,
                category=category,
                start_date=start_date,
                end_date=end_date,
            ).scalar()
        )
        if prior_avg:
            seven_day_change_pct = ((latest_avg_price - prior_avg) / prior_avg) * 100.0

    return {
        "record_count": int(aggregate.record_count or 0),
        "avg_price_per_kg": _as_float(aggregate.avg_price_per_kg),
        "total_arrival_quantity": _as_float(aggregate.total_arrival_quantity),
        "unique_markets": unique_markets,
        "latest_date": latest_date.isoformat() if latest_date else None,
        "latest_avg_price_per_kg": latest_avg_price,
        "seven_day_change_pct": round(seven_day_change_pct, 2),
    }


@router.get("/prices/timeseries", tags=["Prices"])
def get_prices_timeseries(
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
    category: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    days: int = Query(120, ge=7, le=3650),
):
    """Server-side daily aggregation for chart rendering with reduced payload."""
    if not start_date and not end_date:
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)

    query = _apply_price_filters(
        db.query(
            models.PriceRecord.date.label("date"),
            func.avg(models.PriceRecord.modal_price).label("avg_modal_price"),
            func.sum(models.PriceRecord.arrival_quantity).label("total_arrival_quantity"),
            func.count(models.PriceRecord.id).label("observations"),
        )
        .select_from(models.PriceRecord)
        .join(models.Market, models.PriceRecord.market_id == models.Market.id)
        .join(models.District, models.Market.district_id == models.District.id)
        .join(models.State, models.District.state_id == models.State.id)
        .join(models.Source, models.PriceRecord.source_id == models.Source.id)
        .join(models.Commodity, models.PriceRecord.commodity_id == models.Commodity.id)
        .join(models.Variety, models.PriceRecord.variety_id == models.Variety.id),
        commodity_id=commodity_id,
        commodity_name=commodity_name,
        variety_id=variety_id,
        variety_name=variety_name,
        market_id=market_id,
        market_name=market_name,
        state_name=state_name,
        source_id=source_id,
        source_name=source_name,
        category=category,
        start_date=start_date,
        end_date=end_date,
    )
    rows = query.group_by(models.PriceRecord.date).order_by(models.PriceRecord.date.asc()).all()
    series = [
        {
            "date": row.date.isoformat() if row.date else None,
            "avg_modal_price": _as_float(row.avg_modal_price),
            "total_arrival_quantity": _as_float(row.total_arrival_quantity),
            "observations": int(row.observations or 0),
        }
        for row in rows
    ]
    return {"count": len(series), "series": series}


@router.get("/prices/commodity/{commodity_id}", tags=["Prices"])
def get_commodity_prices(
    commodity_id: int,
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
    source_filter: Optional[str] = Query(None),
):
    """Get price history for a specific commodity."""
    cutoff_date = datetime.now().date()
    start_date = cutoff_date - timedelta(days=days)
    query = db.query(models.PriceRecord).filter(
        models.PriceRecord.commodity_id == commodity_id,
        models.PriceRecord.date >= start_date,
        models.PriceRecord.date <= cutoff_date,
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
        "prices": prices,
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
    limit: int = Query(500, ge=1, le=5000),
):
    """Get all markets with optional state filtering."""
    query = (
        db.query(
            models.Market,
            models.State.name.label("state_name"),
            models.District.name.label("district_name"),
        )
        .join(models.District, models.Market.district_id == models.District.id)
        .join(models.State, models.District.state_id == models.State.id)
    )

    if state_id:
        query = query.filter(models.District.state_id == state_id)
    elif state_name:
        query = query.filter(models.State.name.ilike(f"%{state_name}%"))

    results = query.offset(skip).limit(limit).all()

    final_markets = []
    for m, s_name, d_name in results:
        m.state_name = s_name
        m.district_name = d_name
        final_markets.append(m)

    return final_markets


@router.get("/markets/search", tags=["Markets"])
def search_markets(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    """Search markets by name."""
    results = (
        db.query(models.Market)
        .filter(models.Market.name.ilike(f"%{q}%"))
        .limit(50)
        .all()
    )
    return {"query": q, "results": results, "count": len(results)}


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
    """Get all available data sources."""
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
            "MCX",
            "FMPIS",
        ],
    }


# ============================================================================
# FORECAST ENDPOINTS
# ============================================================================


@router.get("/forecast/all", tags=["Forecasting"])
def get_all_forecasts(
    db: Session = Depends(get_db), weeks: int = Query(6, ge=1, le=12)
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
        except:
            continue
    return {"forecast_count": len(forecasts), "forecasts": forecasts, "weeks": weeks}


@router.get("/analytics/supply-demand", tags=["Analytics"])
def get_supply_demand_analytics(
    crop: Optional[str] = Query(None),
):
    """Return the unified cross-crop supply-demand snapshot derived from local support stores."""
    rows = _fetch_supply_demand_rows()
    if crop:
        rows = [row for row in rows if str(row.get("crop", "")).lower() == crop.lower()]
    return {
        "status": "success",
        "count": len(rows),
        "rows": rows,
    }


@router.get("/analytics/supply-demand-history", tags=["Analytics"])
def get_supply_demand_history(
    crop: Optional[str] = Query(None),
):
    """Return annual delta history where delta is total available volume minus total deductions."""
    rows = _fetch_supply_demand_delta_history(crop)
    return {
        "status": "success",
        "count": len(rows),
        "rows": rows,
    }


@router.get("/analytics/dashboard", tags=["Analytics"])
def get_analytics_dashboard(
    commodity: str = Query("Wheat"),
):
    """Return live analytics payload for the selected crop including risk frame, heatmap, scenarios, and geography."""
    service = AnalyticsDashboardService()
    try:
        return service.build(commodity)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Analytics dashboard generation failed")
        raise HTTPException(status_code=500, detail=f"Failed to generate analytics dashboard: {exc}") from exc


@router.get("/forecast/wheat/monte-carlo", tags=["Forecasting"])
def get_wheat_monte_carlo_forecast(
    days: int = Query(30, ge=7, le=120),
    simulations: int = Query(2000, ge=100, le=10000),
):
    """Generate a wheat price forecast from the local AGMARKNET historical SQLite dump."""
    forecaster = WheatMonteCarloForecaster()
    forecast = forecaster.generate_forecast(
        horizon_days=days,
        simulation_count=simulations,
    )
    if forecast.get("status") == "error":
        raise HTTPException(status_code=404, detail=forecast["message"])
    return forecast


@router.get("/forecast/wheat/history", tags=["Forecasting"])
def get_wheat_local_history(
    days: int = Query(180, ge=30, le=730),
):
    """Return recent Wheat daily price history from the local AGMARKNET SQLite store."""
    forecaster = WheatMonteCarloForecaster()
    payload = forecaster.get_recent_history(days=days)
    if payload.get("status") == "error":
        raise HTTPException(status_code=404, detail=payload["message"])
    return payload


@router.get("/forecast/wheat/ml", tags=["Forecasting"])
def get_wheat_ml_forecast(
    days: int = Query(42, ge=7, le=120),
    simulations: int = Query(2000, ge=100, le=10000),
):
    """Generate the preferred Wheat forecast using the local feature model anchored with Monte Carlo bands."""
    forecaster = WheatFeatureForecaster()
    try:
        return forecaster.forecast(horizon_days=days, simulations=simulations)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/forecast/rice/monte-carlo", tags=["Forecasting"])
def get_rice_monte_carlo_forecast(
    days: int = Query(30, ge=7, le=120),
    simulations: int = Query(2000, ge=100, le=10000),
):
    """Generate a rice price forecast from the local AGMARKNET historical SQLite dump."""
    forecaster = RiceMonteCarloForecaster()
    forecast = forecaster.generate_forecast(
        horizon_days=days,
        simulation_count=simulations,
    )
    if forecast.get("status") == "error":
        raise HTTPException(status_code=404, detail=forecast["message"])
    return forecast


@router.get("/forecast/rice/history", tags=["Forecasting"])
def get_rice_local_history(
    days: int = Query(180, ge=30, le=730),
):
    """Return recent Rice daily price history from the local AGMARKNET SQLite store."""
    forecaster = RiceMonteCarloForecaster()
    payload = forecaster.get_recent_history(days=days)
    if payload.get("status") == "error":
        raise HTTPException(status_code=404, detail=payload["message"])
    return payload


@router.get("/forecast/rice/ml", tags=["Forecasting"])
def get_rice_ml_forecast(
    days: int = Query(42, ge=7, le=120),
    simulations: int = Query(2000, ge=100, le=10000),
):
    """Generate the preferred Rice forecast using the local feature model anchored with Monte Carlo bands."""
    forecaster = RiceFeatureForecaster()
    try:
        return forecaster.forecast(horizon_days=days, simulations=simulations)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/forecast/maize/monte-carlo", tags=["Forecasting"])
def get_maize_monte_carlo_forecast(
    days: int = Query(30, ge=7, le=120),
    simulations: int = Query(2000, ge=100, le=10000),
):
    """Generate a maize price forecast from the local AGMARKNET historical SQLite dump."""
    forecaster = MaizeMonteCarloForecaster()
    forecast = forecaster.generate_forecast(
        horizon_days=days,
        simulation_count=simulations,
    )
    if forecast.get("status") == "error":
        raise HTTPException(status_code=404, detail=forecast["message"])
    return forecast


@router.get("/forecast/maize/history", tags=["Forecasting"])
def get_maize_local_history(
    days: int = Query(180, ge=30, le=730),
):
    """Return recent Maize daily price history from the local AGMARKNET SQLite store."""
    forecaster = MaizeMonteCarloForecaster()
    payload = forecaster.get_recent_history(days=days)
    if payload.get("status") == "error":
        raise HTTPException(status_code=404, detail=payload["message"])
    return payload


@router.get("/forecast/maize/ml", tags=["Forecasting"])
def get_maize_ml_forecast(
    days: int = Query(42, ge=7, le=120),
    simulations: int = Query(2000, ge=100, le=10000),
):
    """Generate the preferred Maize forecast using the local feature model anchored with Monte Carlo bands."""
    forecaster = MaizeFeatureForecaster()
    try:
        return forecaster.forecast(horizon_days=days, simulations=simulations)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/forecast/{commodity_id}", tags=["Forecasting"])
def get_forecast(
    commodity_id: int, db: Session = Depends(get_db), weeks: int = Query(6, ge=1, le=12)
):
    """Get multi-week price forecast for a commodity."""
    commodity = db.query(models.Commodity).filter_by(id=commodity_id).first()
    if not commodity:
        raise HTTPException(status_code=404, detail="Commodity not found")
    forecaster = MultiSignalForecaster(db)
    forecast = forecaster.get_forecast(commodity_id, weeks)
    if "error" in forecast:
        raise HTTPException(status_code=400, detail=forecast["error"])
    return forecast


# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================


@router.get("/analytics/daily-average", tags=["Analytics"])
@router.get("/insights/daily-average", tags=["Analytics"])
def get_daily_average(commodity_id: int, db: Session = Depends(get_db)):
    """Get daily average price for a commodity."""
    avg_price = (
        db.query(func.avg(models.PriceRecord.modal_price))
        .filter(models.PriceRecord.commodity_id == commodity_id)
        .scalar()
    )
    avg_normalized = (
        db.query(func.avg(models.PriceRecord.normalized_price_per_kg))
        .filter(models.PriceRecord.commodity_id == commodity_id)
        .scalar()
    )
    if avg_price is None:
        raise HTTPException(status_code=404, detail="No data found")
    return {
        "commodity_id": commodity_id,
        "average_price": float(avg_price),
        "average_price_per_kg": float(avg_normalized or (avg_price / 100)),
        "unit": "INR",
    }


@router.get("/analytics/price-range", tags=["Analytics"])
def get_price_range(
    commodity_id: int,
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
):
    """Get min/max/avg prices for a commodity over a period."""
    start_date = datetime.now().date() - timedelta(days=days)
    records = (
        db.query(models.PriceRecord)
        .filter(
            models.PriceRecord.commodity_id == commodity_id,
            models.PriceRecord.date >= start_date,
        )
        .all()
    )
    if not records:
        raise HTTPException(status_code=404, detail="No data found")
    prices = [float(r.modal_price) for r in records]
    return {
        "commodity_id": commodity_id,
        "period_days": days,
        "min_price": min(prices),
        "max_price": max(prices),
        "avg_price": sum(prices) / len(prices),
        "record_count": len(prices),
    }


@router.get("/analytics/source-comparison", tags=["Analytics"])
def get_source_comparison(
    commodity_id: int,
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
):
    """Compare prices across different data sources."""
    start_date = datetime.now().date() - timedelta(days=days)
    results = (
        db.query(
            models.Source.name,
            func.avg(models.PriceRecord.modal_price).label("avg_price"),
            func.min(models.PriceRecord.modal_price).label("min_price"),
            func.max(models.PriceRecord.modal_price).label("max_price"),
            func.count(models.PriceRecord.id).label("record_count"),
        )
        .join(models.Source)
        .filter(
            models.PriceRecord.commodity_id == commodity_id,
            models.PriceRecord.date >= start_date,
        )
        .group_by(models.Source.name)
        .all()
    )
    if not results:
        raise HTTPException(status_code=404, detail="No data found")
    comparison = []
    for source_name, avg_p, min_p, max_p, count in results:
        comparison.append(
            {
                "source": source_name,
                "avg_price": float(avg_p) if avg_p else 0,
                "min_price": float(min_p) if min_p else 0,
                "max_price": float(max_p) if max_p else 0,
                "record_count": count,
            }
        )
    return {"commodity_id": commodity_id, "period_days": days, "sources": comparison}


@router.get("/analytics/terminal-summary", tags=["Analytics"])
def get_terminal_summary(
    commodity_terms: List[str] = Query(...),
    db: Session = Depends(get_db),
):
    """Get a live summary for the terminal page using commodity names and aliases."""
    normalized_terms = [term.strip() for term in commodity_terms if term and term.strip()]
    if not normalized_terms:
        raise HTTPException(status_code=400, detail="At least one commodity term is required")

    query = (
        db.query(
            models.PriceRecord,
            models.Market.name.label("market_name"),
            models.State.name.label("state_name"),
            models.Source.name.label("source_name"),
            models.Commodity.name.label("commodity_name"),
            models.Variety.name.label("variety_name"),
        )
        .join(models.Market, models.PriceRecord.market_id == models.Market.id)
        .join(models.District, models.Market.district_id == models.District.id)
        .join(models.State, models.District.state_id == models.State.id)
        .join(models.Source, models.PriceRecord.source_id == models.Source.id)
        .join(models.Commodity, models.PriceRecord.commodity_id == models.Commodity.id)
        .join(models.Variety, models.PriceRecord.variety_id == models.Variety.id)
    )

    search_filter = (
        models.Commodity.name.ilike(f"%{normalized_terms[0]}%")
        | models.Variety.name.ilike(f"%{normalized_terms[0]}%")
    )
    for term in normalized_terms[1:]:
        search_filter = (
            search_filter
            | models.Commodity.name.ilike(f"%{term}%")
            | models.Variety.name.ilike(f"%{term}%")
        )

    try:
        rows = query.filter(search_filter).order_by(models.PriceRecord.date.desc()).limit(500).all()
    except OperationalError:
        return {
            "commodity_terms": normalized_terms,
            "latest_date": None,
            "kpis": [],
            "price_series": [],
            "arrivals": [],
            "meta": {"record_count": 0, "latest_record_count": 0, "sources": []},
        }
    if not rows:
        return {
            "commodity_terms": normalized_terms,
            "latest_date": None,
            "kpis": [],
            "price_series": [],
            "arrivals": [],
            "meta": {"record_count": 0, "latest_record_count": 0, "sources": []},
        }

    flattened = []
    for pr, market_name, state_name, source_name, commodity_name, variety_name in rows:
        flattened.append(
            {
                "date": pr.date,
                "market_name": market_name,
                "state_name": state_name,
                "source_name": source_name,
                "commodity_name": commodity_name,
                "variety_name": variety_name,
                "modal_price": _as_float(pr.modal_price),
                "arrival_quantity": _as_float(pr.arrival_quantity),
                "unit": pr.unit or "Unknown",
            }
        )

    latest_date = max(item["date"] for item in flattened if item["date"] is not None)
    latest_rows = [item for item in flattened if item["date"] == latest_date]
    latest_avg_price = sum(item["modal_price"] for item in latest_rows) / max(len(latest_rows), 1)
    latest_arrivals = sum(item["arrival_quantity"] for item in latest_rows)

    def avg_price_for_days(days: int) -> float:
        cutoff = latest_date - timedelta(days=days)
        values = [item["modal_price"] for item in flattened if item["date"] and item["date"] >= cutoff]
        return sum(values) / len(values) if values else 0.0

    avg_7 = avg_price_for_days(7)
    avg_30 = avg_price_for_days(30)

    def pct_change(current: float, baseline: float) -> float:
        if not baseline:
            return 0.0
        return ((current - baseline) / baseline) * 100

    seven_day_change = pct_change(latest_avg_price, avg_7)
    thirty_day_change = pct_change(latest_avg_price, avg_30)

    grouped_by_date = {}
    for item in flattened:
        if item["date"] is None:
            continue
        key = item["date"].isoformat()
        grouped_by_date.setdefault(key, []).append(item["modal_price"])

    price_series = [
        {"label": key, "price": round(sum(values) / len(values), 2)}
        for key, values in sorted(grouped_by_date.items())[-7:]
    ]

    arrivals_by_market = {}
    for item in latest_rows:
        key = (item["market_name"], item["state_name"])
        arrivals_by_market[key] = arrivals_by_market.get(key, 0.0) + item["arrival_quantity"]

    arrivals = [
        {"market": market, "state": state, "arrivals": round(quantity, 2)}
        for (market, state), quantity in sorted(arrivals_by_market.items(), key=lambda row: row[1], reverse=True)[:5]
    ]

    unit = latest_rows[0]["unit"] if latest_rows else ""
    source_names = sorted({item["source_name"] for item in flattened if item["source_name"]})
    outlook = "Bullish" if seven_day_change > 1 else "Bearish" if seven_day_change < -1 else "Range-Bound"

    kpis = [
        {
            "label": "Benchmark Price",
            "value": round(latest_avg_price, 2),
            "change": round(seven_day_change, 2),
            "type": "positive" if seven_day_change > 0 else "negative" if seven_day_change < 0 else "neutral",
            "suffix": unit,
        },
        {
            "label": "7-Day Change",
            "value": round(seven_day_change, 2),
            "change": round(seven_day_change, 2),
            "type": "positive" if seven_day_change > 0 else "negative" if seven_day_change < 0 else "neutral",
            "suffix": "%",
        },
        {
            "label": "30-Day Change",
            "value": round(thirty_day_change, 2),
            "change": round(thirty_day_change, 2),
            "type": "positive" if thirty_day_change > 0 else "negative" if thirty_day_change < 0 else "neutral",
            "suffix": "%",
        },
        {
            "label": "Arrivals",
            "value": round(latest_arrivals, 2),
            "change": 0,
            "type": "neutral",
            "suffix": unit,
        },
        {
            "label": "Markets",
            "value": len({item["market_name"] for item in latest_rows}),
            "change": 0,
            "type": "neutral",
            "suffix": "",
        },
        {
            "label": "Sources",
            "value": len(source_names),
            "change": 0,
            "type": "neutral",
            "suffix": "",
        },
        {
            "label": "Latest Date",
            "value": latest_date.isoformat(),
            "change": 0,
            "type": "neutral",
            "suffix": "",
        },
        {
            "label": "Outlook",
            "value": outlook,
            "change": round(seven_day_change, 2),
            "type": "positive" if outlook == "Bullish" else "negative" if outlook == "Bearish" else "neutral",
            "suffix": "",
        },
    ]

    return {
        "commodity_terms": normalized_terms,
        "latest_date": latest_date.isoformat(),
        "kpis": kpis,
        "price_series": price_series,
        "arrivals": arrivals,
        "meta": {
            "record_count": len(flattened),
            "latest_record_count": len(latest_rows),
            "sources": source_names,
        },
    }


# ============================================================================
# INGESTION ENDPOINTS
# ============================================================================


@router.post("/ingest", tags=["Ingestion"])
async def trigger_ingestion(
    background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """Trigger background data ingestion cycle."""
    from app.ingestion.pipeline_orchestrator import commodity_ingestion_pipeline

    background_tasks.add_task(commodity_ingestion_pipeline, datetime.now())
    return {
        "status": "success",
        "message": "Ingestion cycle started in background",
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/ingest/{source_name}", tags=["Ingestion"])
def trigger_source_ingestion(source_name: str, db: Session = Depends(get_db)):
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
            "normalized_records": len(normalized_data),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/agmarknet/today", tags=["Ingestion"])
def ingest_today_agmarknet(
    run_date: Optional[date] = Query(None),
    allow_mock_fallback: bool = Query(False),
    dry_run: bool = Query(False),
    page_size: int = Query(100, ge=1, le=500),
    max_pages: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Fast path to fetch today's AGMARKNET prices and upsert them into the warehouse."""
    try:
        service = DailyAgmarknetSyncService(db)
        result = service.run(
            datetime.combine(run_date or datetime.now().date(), datetime.min.time()),
            allow_mock_fallback=allow_mock_fallback,
            dry_run=dry_run,
            page_size=page_size,
            max_pages=max_pages,
        )
        return {
            "status": "success",
            "message": "AGMARKNET daily sync completed" if not dry_run else "AGMARKNET daily sync dry-run completed",
            "result": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MPEDA ENDPOINTS
# ============================================================================


@router.get("/mpeda/export-data", tags=["Marine Data"])
def get_mpeda_export_data(
    commodity: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    """Get MPEDA marine export data."""
    from app.services.mpeda_downloader import (
        load_latest_data,
        download_mpeda_data,
        parse_item_wise_data,
    )

    try:
        df = load_latest_data("item")
        if df is None:
            df = download_mpeda_data("item")
        if df is None:
            raise HTTPException(status_code=503, detail="Unable to fetch MPEDA data")
        records = parse_item_wise_data(df)
        if commodity:
            records = [
                r for r in records if commodity.lower() in r["commodity"].lower()
            ]
        if year:
            records = [r for r in records if r["year"] == year]
        return {"source": "MPEDA", "count": len(records), "records": records[:limit]}
    except Exception as e:
        logger.error(f"MPEDA Error: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/mpeda/refresh", tags=["Marine Data"])
def refresh_mpeda_data():
    """Force refresh MPEDA data from source."""
    from app.services.mpeda_downloader import download_mpeda_data, parse_item_wise_data

    df = download_mpeda_data("item")
    if df is None:
        raise HTTPException(status_code=503, detail="Failed to download MPEDA data")
    records = parse_item_wise_data(df)
    return {"status": "success", "source": "MPEDA", "records_count": len(records)}


@router.get("/mpeda/commodities", tags=["Marine Data"])
def get_mpeda_commodities():
    """Get list of available marine export commodities."""
    from app.services.mpeda_downloader import (
        load_latest_data,
        download_mpeda_data,
        parse_item_wise_data,
    )

    df = load_latest_data("item") or download_mpeda_data("item")
    if df is None:
        raise HTTPException(status_code=503, detail="Unable to fetch MPEDA data")
    records = parse_item_wise_data(df)
    commodities = sorted(list(set(r["commodity"] for r in records)))
    return {"commodities": commodities, "count": len(commodities)}


# ============================================================================
# MARINE (FMPIS) ENDPOINTS
# ============================================================================


@router.get("/marine/states", tags=["Marine"])
def get_marine_states(db: Session = Depends(get_db)):
    """Get all states that have marine commodity data."""
    cache = get_cache()
    if cache.enabled:
        cached = cache.get_marine_states()
        if cached:
            return cached

    states = (
        db.query(distinct(models.State.name))
        .join(models.District, models.State.id == models.District.state_id)
        .join(models.Market, models.District.id == models.Market.district_id)
        .join(models.PriceRecord, models.Market.id == models.PriceRecord.market_id)
        .join(models.Commodity, models.PriceRecord.commodity_id == models.Commodity.id)
        .join(models.Source, models.PriceRecord.source_id == models.Source.id)
        .filter(models.Commodity.category == "Marine Products")
        .filter(models.Source.name == "FMPIS")
        .order_by(models.State.name)
        .all()
    )

    result = [s[0] for s in states]
    if cache.enabled:
        cache.set_marine_states(result)
    return result


@router.get("/marine/summary", tags=["Marine"])
def get_marine_summary(db: Session = Depends(get_db)):
    """Get latest marine commodity prices by state."""
    cache = get_cache()
    if cache.enabled:
        cached = cache.get_marine_summary()
        if cached:
            return cached

    records = (
        db.query(
            models.PriceRecord,
            models.Commodity.name.label("commodity_name"),
            models.State.name.label("state_name"),
        )
        .join(models.Commodity, models.PriceRecord.commodity_id == models.Commodity.id)
        .join(models.Market, models.PriceRecord.market_id == models.Market.id)
        .join(models.District, models.Market.district_id == models.District.id)
        .join(models.State, models.District.state_id == models.State.id)
        .join(models.Source, models.PriceRecord.source_id == models.Source.id)
        .filter(models.Commodity.category == "Marine Products")
        .filter(models.Source.name == "FMPIS")
        .order_by(
            models.State.name, models.Commodity.name, models.PriceRecord.date.desc()
        )
        .all()
    )

    summary = {}
    for r, c_name, s_name in records:
        key = f"{s_name}_{c_name}"
        if key not in summary:
            summary[key] = {
                "commodity_name": c_name,
                "state_name": s_name,
                "modal_price": float(r.modal_price),
                "date": r.date.isoformat()
                if hasattr(r.date, "isoformat")
                else str(r.date),
            }

    result = list(summary.values())
    if cache.enabled:
        cache.set_marine_summary(result)
    return result


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
            "Marine Products Support",
            "FMPIS Real-time API",
        ],
    }
