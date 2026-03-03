from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, JSON, Enum, DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class Commodity(Base):
    __tablename__ = "commodities"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    category = Column(String)  # e.g., Grain, Spice, Fruit, Marine
    
    varieties = relationship("Variety", back_populates="commodity")
    price_records = relationship("PriceRecord", back_populates="commodity")

class Variety(Base):
    __tablename__ = "varieties"
    id = Column(Integer, primary_key=True, index=True)
    commodity_id = Column(Integer, ForeignKey("commodities.id"))
    name = Column(String, index=True)
    aliases = Column(JSON, default=[]) # To store fuzzy matching alternates
    
    commodity = relationship("Commodity", back_populates="varieties")
    price_records = relationship("PriceRecord", back_populates="variety")

class State(Base):
    __tablename__ = "states"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    
    districts = relationship("District", back_populates="state")

class District(Base):
    __tablename__ = "districts"
    id = Column(Integer, primary_key=True, index=True)
    state_id = Column(Integer, ForeignKey("states.id"))
    name = Column(String, index=True)
    
    state = relationship("State", back_populates="districts")
    markets = relationship("Market", back_populates="district")

class Market(Base):
    __tablename__ = "markets"
    id = Column(Integer, primary_key=True, index=True)
    district_id = Column(Integer, ForeignKey("districts.id"))
    name = Column(String, index=True)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    
    district = relationship("District", back_populates="markets")
    price_records = relationship("PriceRecord", back_populates="market")

class Source(Base):
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    source_type = Column(String) # Government, Scraping, Private
    
    price_records = relationship("PriceRecord", back_populates="source")

class PriceRecord(Base):
    __tablename__ = "price_records"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    date = Column(Date, index=True)
    commodity_id = Column(Integer, ForeignKey("commodities.id"))
    variety_id = Column(Integer, ForeignKey("varieties.id"))
    market_id = Column(Integer, ForeignKey("markets.id"))
    source_id = Column(Integer, ForeignKey("sources.id"))
    
    min_price = Column(DECIMAL(12, 2))
    max_price = Column(DECIMAL(12, 2))
    modal_price = Column(DECIMAL(12, 2))
    arrival_quantity = Column(DECIMAL(12, 2))
    unit = Column(String) # KG, QUINTAL, TON
    normalized_price_per_kg = Column(DECIMAL(12, 2))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    commodity = relationship("Commodity", back_populates="price_records")
    variety = relationship("Variety", back_populates="price_records")
    market = relationship("Market", back_populates="price_records")
    source = relationship("Source", back_populates="price_records")
