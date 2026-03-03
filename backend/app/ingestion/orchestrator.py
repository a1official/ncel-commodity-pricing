from datetime import datetime
from typing import List
from .connectors import (
    AgmarknetConnector, 
    MarineConnector, 
    AgriwatchConnector,
    TradeIntelligenceConnector,
    MarketSignalsConnector,
    SupplyProductionConnector,
    GlobalMacroConnector
)
from ..services.normalization import NormalizationEngine
from ..core.database import SessionLocal
from ..models import models

class IngestionOrchestrator:
    def __init__(self):
        self.connectors = [
            AgmarknetConnector(),
            MarineConnector(),
            AgriwatchConnector(),
            TradeIntelligenceConnector("Volza"),
            TradeIntelligenceConnector("APEDA"),
            MarketSignalsConnector("NCDEX"),
            MarketSignalsConnector("MCX"),
            SupplyProductionConnector("Govt Stats"),
            SupplyProductionConnector("USDA"),
            GlobalMacroConnector("FAO"),
            GlobalMacroConnector("S&P Global")
        ]
        self.normalization_engine = NormalizationEngine()
        self.db = SessionLocal()

    def run_daily_ingestion(self, date: datetime = None):
        if not date:
            date = datetime.now()
        
        all_standardized_data = []
        for connector in self.connectors:
            print(f"Fetching data from {connector.source_name}...")
            raw_data = connector.fetch_data(date)
            standardized = connector.transform_to_standard(raw_data)
            all_standardized_data.extend(standardized)
            
        print(f"Processing {len(all_standardized_data)} records...")
        self.process_and_save(all_standardized_data)

    def get_or_create_commodity(self, name: str):
        # First try exact match
        commodity = self.db.query(models.Commodity).filter(models.Commodity.name == name).first()
        if not commodity:
            # Try fuzzy matching against existing commodities
            existing = self.db.query(models.Commodity).all()
            choices = [{"id": c.id, "name": c.name} for c in existing]
            matched_id = self.normalization_engine.fuzzy_match(name, choices) if choices else None
            
            if matched_id:
                commodity = self.db.query(models.Commodity).get(matched_id)
            else:
                # Intelligent categorization
                category = "General"
                name_lower = name.lower()
                if any(k in name_lower for k in ["basmati", "white rice", "paddy"]):
                    category = "Rice"
                elif any(k in name_lower for k in ["rice", "wheat", "corn"]):
                    category = "Grains"
                elif any(k in name_lower for k in ["millet", "jowar", "bajra", "ragi", "kodo", "kutki"]):
                    category = "Millets"
                elif any(k in name_lower for k in ["cumin", "turmeric", "chilli", "jeera", "pepper", "dhaniya"]):
                    category = "Spices"
                elif any(k in name_lower for k in ["tomato", "onion", "potato", "grapes", "banana", "pineapple", "apple"]):
                    category = "Fruits & Vegetables"
                elif any(k in name_lower for k in ["shrimp", "trout", "mackerel", "tuna", "pomfret", "prawns"]):
                    category = "Marine Products"
                elif "groundnut" in name_lower:
                    category = "Groundnut"
                elif "maize" in name_lower or "makka" in name_lower:
                    category = "Maize (Makka)"

                commodity = models.Commodity(name=name, category=category)
                self.db.add(commodity)
                self.db.commit()
                self.db.refresh(commodity)
        return commodity

    def get_or_create_variety(self, name: str, commodity_id: int):
        variety = self.db.query(models.Variety).filter(
            models.Variety.name == name, 
            models.Variety.commodity_id == commodity_id
        ).first()
        if not variety:
            # Try fuzzy matching for variety
            existing = self.db.query(models.Variety).filter(models.Variety.commodity_id == commodity_id).all()
            choices = [{"id": v.id, "name": v.name, "aliases": v.aliases or []} for v in existing]
            matched_id = self.normalization_engine.fuzzy_match(name, choices) if choices else None
            
            if matched_id:
                variety = self.db.query(models.Variety).get(matched_id)
            else:
                variety = models.Variety(name=name, commodity_id=commodity_id)
                self.db.add(variety)
                self.db.commit()
                self.db.refresh(variety)
        return variety

    def get_or_create_geo_hierarchy(self, state_name: str, district_name: str, market_name: str):
        # 1. State
        state = self.db.query(models.State).filter(models.State.name == state_name).first()
        if not state:
            state = models.State(name=state_name)
            self.db.add(state)
            self.db.commit()
            self.db.refresh(state)

        # 2. District
        district = self.db.query(models.District).filter(
            models.District.name == district_name,
            models.District.state_id == state.id
        ).first()
        if not district:
            district = models.District(name=district_name, state_id=state.id)
            self.db.add(district)
            self.db.commit()
            self.db.refresh(district)

        # 3. Market
        market = self.db.query(models.Market).filter(
            models.Market.name == market_name,
            models.Market.district_id == district.id
        ).first()
        if not market:
            market = models.Market(name=market_name, district_id=district.id)
            self.db.add(market)
            self.db.commit()
            self.db.refresh(market)
        
        return market
    
    def get_source(self, name: str):
        source = self.db.query(models.Source).filter(models.Source.name == name).first()
        if not source:
            source = models.Source(name=name, source_type="API")
            self.db.add(source)
            self.db.commit()
            self.db.refresh(source)
        return source

    def process_and_save(self, data: List[dict]):
        for record in data:
            # 1. Lookups
            commodity = self.get_or_create_commodity(record["commodity"])
            variety = self.get_or_create_variety(record["variety"], commodity.id)
            market = self.get_or_create_geo_hierarchy(record["state"], record["district"], record["market"])
            source = self.get_source(record["source"])

            # 2. Normalize Unit
            norm_unit = self.normalization_engine.normalize_unit(record["unit"])
            
            # 3. Calculate Price per KG
            price_per_kg = self.normalization_engine.calculate_price_per_kg(
                record["modal_price"], norm_unit
            )
            
            # 4. Save to DB
            price_rec = models.PriceRecord(
                date=record["date"],
                commodity_id=commodity.id,
                variety_id=variety.id,
                market_id=market.id,
                source_id=source.id,
                min_price=record["min_price"],
                max_price=record["max_price"],
                modal_price=record["modal_price"],
                arrival_quantity=record["arrival_quantity"],
                unit=norm_unit,
                normalized_price_per_kg=price_per_kg
            )
            self.db.add(price_rec)
        
        self.db.commit()
        print("Data ingestion complete.")

if __name__ == "__main__":
    orchestrator = IngestionOrchestrator()
    orchestrator.run_daily_ingestion()
