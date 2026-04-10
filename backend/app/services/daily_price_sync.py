from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.ingestion.connectors_enhanced import AgmarknetConnector
from app.models import models
from app.services.normalization import NormalizationEngine


@dataclass
class DailySyncStats:
    source: str
    sync_date: str
    raw_records: int = 0
    normalized_records: int = 0
    deduped_records: int = 0
    created_records: int = 0
    updated_records: int = 0
    skipped_records: int = 0
    dry_run: bool = False

    def as_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "sync_date": self.sync_date,
            "raw_records": self.raw_records,
            "normalized_records": self.normalized_records,
            "deduped_records": self.deduped_records,
            "created_records": self.created_records,
            "updated_records": self.updated_records,
            "skipped_records": self.skipped_records,
            "dry_run": self.dry_run,
        }


class DailyAgmarknetSyncService:
    """Focused daily AGMARKNET sync with idempotent upserts."""

    def __init__(self, db: Session):
        self.db = db
        self.connector = AgmarknetConnector()
        self.normalization = NormalizationEngine(db)

        self._commodity_cache: Dict[str, models.Commodity] = {}
        self._variety_cache: Dict[Tuple[int, str], models.Variety] = {}
        self._state_cache: Dict[str, models.State] = {}
        self._district_cache: Dict[Tuple[int, str], models.District] = {}
        self._market_cache: Dict[Tuple[int, str], models.Market] = {}
        self._source_cache: Dict[str, models.Source] = {}

        self._load_dimension_caches()

    @staticmethod
    def _key(value: Optional[str]) -> str:
        return str(value or "").strip().lower()

    def _load_dimension_caches(self) -> None:
        self._commodity_cache = {
            self._key(row.name): row for row in self.db.query(models.Commodity).all()
        }
        self._state_cache = {
            self._key(row.name): row for row in self.db.query(models.State).all()
        }
        self._source_cache = {
            self._key(row.name): row for row in self.db.query(models.Source).all()
        }

        for row in self.db.query(models.Variety).all():
            self._variety_cache[(row.commodity_id, self._key(row.name))] = row

        for row in self.db.query(models.District).all():
            self._district_cache[(row.state_id, self._key(row.name))] = row

        for row in self.db.query(models.Market).all():
            self._market_cache[(row.district_id, self._key(row.name))] = row

    def _get_or_create_source(self, name: str) -> models.Source:
        key = self._key(name)
        source = self._source_cache.get(key)
        if source:
            return source

        source = models.Source(name=name, source_type="Government")
        self.db.add(source)
        self.db.flush()
        self._source_cache[key] = source
        return source

    def _infer_category(self, commodity_name: str) -> str:
        name = commodity_name.lower()
        if any(token in name for token in ["rice", "paddy", "basmati"]):
            return "Grain"
        if any(token in name for token in ["wheat", "maize", "corn", "millet", "bajra", "jowar", "ragi"]):
            return "Grain"
        if any(token in name for token in ["turmeric", "cumin", "jeera", "chilli", "pepper", "dhaniya"]):
            return "Spice"
        if any(token in name for token in ["banana", "grapes", "pineapple", "apple"]):
            return "Fruit"
        if any(token in name for token in ["onion", "potato", "tomato"]):
            return "Vegetable"
        return "General"

    def _get_or_create_commodity(self, name: str) -> models.Commodity:
        key = self._key(name)
        commodity = self._commodity_cache.get(key)
        if commodity:
            return commodity

        choices = [{"id": row.id, "name": row.name} for row in self._commodity_cache.values()]
        matched_id = self.normalization.fuzzy_match(name, choices) if choices else None
        if matched_id:
            commodity = self.db.query(models.Commodity).filter(models.Commodity.id == matched_id).first()
            if commodity:
                self._commodity_cache[key] = commodity
                return commodity

        commodity = models.Commodity(name=name, category=self._infer_category(name))
        self.db.add(commodity)
        self.db.flush()
        self._commodity_cache[key] = commodity
        return commodity

    def _get_or_create_variety(self, commodity_id: int, name: Optional[str]) -> models.Variety:
        variety_name = (name or "Standard").strip() or "Standard"
        key = (commodity_id, self._key(variety_name))
        variety = self._variety_cache.get(key)
        if variety:
            return variety

        choices = [
            {"id": row.id, "name": row.name, "aliases": row.aliases or []}
            for cache_key, row in self._variety_cache.items()
            if cache_key[0] == commodity_id
        ]
        matched_id = self.normalization.fuzzy_match(variety_name, choices) if choices else None
        if matched_id:
            variety = self.db.query(models.Variety).filter(models.Variety.id == matched_id).first()
            if variety:
                self._variety_cache[key] = variety
                return variety

        variety = models.Variety(name=variety_name, commodity_id=commodity_id)
        self.db.add(variety)
        self.db.flush()
        self._variety_cache[key] = variety
        return variety

    def _get_or_create_state(self, name: str) -> models.State:
        key = self._key(name)
        state = self._state_cache.get(key)
        if state:
            return state

        state = models.State(name=name)
        self.db.add(state)
        self.db.flush()
        self._state_cache[key] = state
        return state

    def _get_or_create_district(self, state_id: int, name: str) -> models.District:
        key = (state_id, self._key(name))
        district = self._district_cache.get(key)
        if district:
            return district

        district = models.District(name=name, state_id=state_id)
        self.db.add(district)
        self.db.flush()
        self._district_cache[key] = district
        return district

    def _get_or_create_market(self, district_id: int, name: str) -> models.Market:
        key = (district_id, self._key(name))
        market = self._market_cache.get(key)
        if market:
            return market

        market = models.Market(name=name, district_id=district_id)
        self.db.add(market)
        self.db.flush()
        self._market_cache[key] = market
        return market

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        return Decimal(str(value))

    def run(
        self,
        sync_datetime: Optional[datetime] = None,
        *,
        allow_mock_fallback: bool = False,
        dry_run: bool = False,
        page_size: int = 100,
        max_pages: int = 200,
    ) -> Dict[str, Any]:
        sync_datetime = sync_datetime or datetime.now()
        stats = DailySyncStats(
            source="AGMARKNET",
            sync_date=sync_datetime.date().isoformat(),
            dry_run=dry_run,
        )

        raw_records = self.connector.fetch_data(
            sync_datetime,
            allow_mock_fallback=allow_mock_fallback,
            page_size=page_size,
            max_pages=max_pages,
        )
        stats.raw_records = len(raw_records)

        normalized_records = self.connector.transform_to_standard(raw_records)
        stats.normalized_records = len(normalized_records)

        source = self._get_or_create_source("AGMARKNET")
        existing_records = {
            (
                row.commodity_id,
                row.variety_id,
                row.market_id,
                row.source_id,
                row.date.isoformat(),
            ): row
            for row in self.db.query(models.PriceRecord)
            .filter(
                models.PriceRecord.date == sync_datetime.date(),
                models.PriceRecord.source_id == source.id,
            )
            .all()
        }

        processed_keys = set()

        for record in normalized_records:
            try:
                commodity = self._get_or_create_commodity(record["commodity"])
                variety = self._get_or_create_variety(commodity.id, record.get("variety"))
                state = self._get_or_create_state(record["state"])
                district = self._get_or_create_district(state.id, record["district"])
                market = self._get_or_create_market(district.id, record["market"])

                natural_key = (
                    commodity.id,
                    variety.id,
                    market.id,
                    source.id,
                    record["date"].isoformat(),
                )
                if natural_key in processed_keys:
                    stats.deduped_records += 1
                    continue
                processed_keys.add(natural_key)

                existing = existing_records.get(natural_key)
                payload = {
                    "min_price": self._to_decimal(record["min_price"]),
                    "max_price": self._to_decimal(record["max_price"]),
                    "modal_price": self._to_decimal(record["modal_price"]),
                    "arrival_quantity": self._to_decimal(record.get("arrival_quantity", 0)),
                    "unit": self.normalization.normalize_unit(record.get("unit", "QUINTAL")),
                    "normalized_price_per_kg": self._to_decimal(record["normalized_price_per_kg"]),
                }

                if existing:
                    for field, value in payload.items():
                        setattr(existing, field, value)
                    stats.updated_records += 1
                    continue

                price_record = models.PriceRecord(
                    date=record["date"],
                    commodity_id=commodity.id,
                    variety_id=variety.id,
                    market_id=market.id,
                    source_id=source.id,
                    **payload,
                )
                self.db.add(price_record)
                existing_records[natural_key] = price_record
                stats.created_records += 1
            except Exception:
                stats.skipped_records += 1

        if dry_run:
            self.db.rollback()
        else:
            self.db.commit()

        return stats.as_dict()
