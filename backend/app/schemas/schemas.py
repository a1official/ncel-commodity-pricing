from pydantic import BaseModel
from typing import List, Optional
from datetime import date as date_type
from decimal import Decimal

# Commodity Schemas
class CommodityBase(BaseModel):
    name: str
    category: str

class CommodityCreate(CommodityBase):
    pass

class Commodity(CommodityBase):
    id: int
    class Config:
        from_attributes = True

# Variety Schemas
class VarietyBase(BaseModel):
    name: str
    commodity_id: int
    aliases: List[str] = []

class VarietyCreate(VarietyBase):
    pass

class Variety(VarietyBase):
    id: int
    class Config:
        from_attributes = True

# Market Schemas
class MarketBase(BaseModel):
    name: str
    district_id: int

class MarketCreate(MarketBase):
    pass

class Market(MarketBase):
    id: int
    lat: Optional[float] = None
    lon: Optional[float] = None
    state_name: Optional[str] = None
    district_name: Optional[str] = None
    class Config:
        from_attributes = True

# Price Record Schemas
class PriceRecordBase(BaseModel):
    date: date_type
    commodity_id: int
    variety_id: int
    market_id: int
    source_id: int
    min_price: Decimal
    max_price: Decimal
    modal_price: Decimal
    arrival_quantity: Decimal
    unit: str
    normalized_price_per_kg: Decimal

class PriceRecord(PriceRecordBase):
    id: str
    market_name: Optional[str] = None
    state_name: Optional[str] = None
    source_name: Optional[str] = None
    commodity_name: Optional[str] = None
    variety_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class PriceFilter(BaseModel):
    start_date: Optional[date_type] = None
    end_date: Optional[date_type] = None
    commodity_id: Optional[int] = None
    variety_id: Optional[int] = None
    state_id: Optional[int] = None
    market_id: Optional[int] = None
