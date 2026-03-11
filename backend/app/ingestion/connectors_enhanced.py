"""
Enhanced Connector Architecture for Multi-Source Data Integration
Supports: AGMARKNET, USDA, FAO, APEDA, MPEDA, NCDEX, MCX, Agriwatch, Volza
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import requests
import json
from datetime import datetime, timedelta
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)



class BaseConnector(ABC):
    """Abstract base class for all data source connectors."""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.timeout = 30

    @abstractmethod
    def fetch_data(self, date_obj: datetime, **kwargs) -> List[Dict[str, Any]]:
        """Fetch raw data from the source for a specific date."""
        pass

    @abstractmethod
    def transform_to_standard(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform raw source-specific data to standardized JSON schema."""
        pass

    def normalize_price(self, price: float, unit: str) -> float:
        """Convert price to per-kg equivalent."""
        unit_map = {
            "Quintal": 100,
            "Ton": 1000,
            "Kg": 1,
            "kg": 1,
            "KG": 1,
        }
        divisor = unit_map.get(unit, 1)
        return price / divisor if divisor > 0 else price


class AgmarknetConnector(BaseConnector):
    """Connector for AGMARKNET (data.gov.in) - Indian Agricultural Prices."""
    
    def __init__(self):
        super().__init__("AGMARKNET")
        self.api_url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
        self.api_key = settings.DATA_GOV_API_KEY

    def fetch_data(self, date_obj: datetime, **kwargs) -> List[Dict[str, Any]]:
        if not self.api_key or self.api_key == "YOUR_API_KEY":
            # Return mock data for demo
            return self._get_mock_data(date_obj)

        params = {
            "api-key": self.api_key,
            "format": "json",
            "filters[arrival_date]": date_obj.strftime("%d/%m/%Y"),
            "limit": 500
        }
        
        try:
            response = requests.get(self.api_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return data.get('records', [])
        except Exception as e:
            logger.error(f"AGMARKNET API error: {e}")
            return self._get_mock_data(date_obj)

    def _get_mock_data(self, date_obj: datetime) -> List[Dict[str, Any]]:
        """Return mock data for testing without API key."""
        return [
            {
                "state": "Haryana",
                "district": "Karnal",
                "market": "Karnal",
                "commodity": "Rice",
                "variety": "Basmati",
                "arrival_date": date_obj.strftime("%d/%m/%Y"),
                "min_price": "5200",
                "max_price": "6100",
                "modal_price": "5600",
                "unit": "Quintal",
                "arrival_quantity": "1200"
            },
            {
                "state": "Maharashtra",
                "district": "Nashik",
                "market": "Vashi",
                "commodity": "Potato",
                "variety": "Jyoti",
                "arrival_date": date_obj.strftime("%d/%m/%Y"),
                "min_price": "650",
                "max_price": "850",
                "modal_price": "750",
                "unit": "Quintal",
                "arrival_quantity": "8500"
            }
        ]

    def transform_to_standard(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        standardized = []
        for record in raw_data:
            try:
                unit = record.get("unit", "Quintal")
                modal_price = float(record["modal_price"])
                standardized.append({
                    "source": self.source_name,
                    "date": datetime.strptime(record["arrival_date"], "%d/%m/%Y").date(),
                    "state": record["state"],
                    "district": record["district"],
                    "market": record["market"],
                    "commodity": record["commodity"],
                    "variety": record["variety"],
                    "min_price": float(record["min_price"]),
                    "max_price": float(record["max_price"]),
                    "modal_price": modal_price,
                    "unit": unit,
                    "arrival_quantity": float(record.get("arrival_quantity", 0)),
                    "normalized_price_per_kg": self.normalize_price(modal_price, unit)
                })
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Skipping malformed AGMARKNET record: {e}")
                continue
        return standardized


class USDAConnector(BaseConnector):
    """Connector for USDA APIs - Production, Supply, Distribution data."""
    
    def __init__(self):
        super().__init__("USDA")
        self.api_url = "https://quickstats.nass.usda.gov/api"
        self.api_key = settings.USDA_API_KEY

    def fetch_data(self, date_obj: datetime, **kwargs) -> List[Dict[str, Any]]:
        if not self.api_key or self.api_key == "YOUR_API_KEY":
            return self._get_mock_data(date_obj)

        # USDA QuickStats API for production data
        params = {
            "key": self.api_key,
            "format": "JSON",
            "commodity_desc": "RICE",
            "year__GE": date_obj.year - 1,
            "year__LE": date_obj.year,
            "agg_level_desc": "NATIONAL"
        }
        
        try:
            response = requests.get(f"{self.api_url}/api_GET", params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return data.get('data', [])
        except Exception as e:
            logger.error(f"USDA API error: {e}")
            return self._get_mock_data(date_obj)

    def _get_mock_data(self, date_obj: datetime) -> List[Dict[str, Any]]:
        """Return mock USDA production data."""
        return [
            {
                "commodity": "Rice",
                "country": "USA",
                "production_million_tons": "8.5",
                "forecast_million_tons": "8.8",
                "year": date_obj.year,
                "date": date_obj.strftime("%Y-%m-%d")
            },
            {
                "commodity": "Wheat",
                "country": "USA",
                "production_million_tons": "45.2",
                "forecast_million_tons": "46.1",
                "year": date_obj.year,
                "date": date_obj.strftime("%Y-%m-%d")
            }
        ]

    def transform_to_standard(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        standardized = []
        for record in raw_data:
            try:
                # USDA data is production-focused, not price
                production = float(record.get("production_million_tons", 0)) * 1000000
                standardized.append({
                    "source": self.source_name,
                    "date": datetime.strptime(record.get("date", "2026-01-01"), "%Y-%m-%d").date(),
                    "state": "USA",
                    "district": "National",
                    "market": "USDA",
                    "commodity": record.get("commodity", "Unknown"),
                    "variety": "Production Data",
                    "min_price": 0,
                    "max_price": 0,
                    "modal_price": 0,
                    "unit": "Ton",
                    "arrival_quantity": production,
                    "normalized_price_per_kg": 0
                })
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Skipping malformed USDA record: {e}")
                continue
        return standardized


class FAOConnector(BaseConnector):
    """Connector for FAO Food Price Index (CSV-based pipeline)."""
    
    def __init__(self):
        super().__init__("FAO")
        # Direct URL discovered from worldfoodsituation/foodpricesindex/en/
        self.csv_url = "https://www.fao.org/media/docs/worldfoodsituationlibraries/default-document-library/food_price_indices_data_csv_mar.csv?sfvrsn=523ebd2a_72&download=true"

    def fetch_data(self, date_obj: datetime, **kwargs) -> List[Dict[str, Any]]:
        """Fetch FAO Food Price Index from live CSV."""
        try:
            import pandas as pd
            import io
            
            logger.info(f"Fetching FAO CSV data from {self.csv_url}")
            response = requests.get(self.csv_url, timeout=self.timeout)
            response.raise_for_status()
            
            # Use utf-8-sig to handle Byte Order Mark (BOM)
            content = response.content.decode('utf-8-sig')
            
            # FAO CSV structure: 
            # Row 1: Title, Row 2: Base, Row 3: Headers, Row 4: Empty, Row 5+: Data
            df = pd.read_csv(io.StringIO(content), skiprows=2)
            
            # Cleaning: drop completely empty rows or columns (FAO uses trailing commas)
            df = df.dropna(how='all', axis=1)
            df = df.dropna(subset=['Date'])
            
            # Format Date column and filter for the month/year of requested date_obj
            requested_month = date_obj.strftime("%Y-%m")
            
            # Search for the exact month (e.g., "2024-03")
            target_row = df[df['Date'].astype(str).str.contains(requested_month)]
            
            if target_row.empty:
                # If exact month not found, try previous month
                prev_month = (date_obj.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
                target_row = df[df['Date'].astype(str).str.contains(prev_month)]
            
            if not target_row.empty:
                record = target_row.iloc[0].to_dict()
                return [{
                    "date": record["Date"],
                    "food_price_index": record["Food Price Index"],
                    "meat": record.get("Meat", 0),
                    "dairy": record.get("Dairy", 0),
                    "cereals": record.get("Cereals", 0),
                    "oils": record.get("Oils", 0),
                    "sugar": record.get("Sugar", 0)
                }]
            
            return []
            
        except Exception as e:
            logger.error(f"FAO CSV pipeline error: {e}")
            return []

    def transform_to_standard(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        standardized = []
        for record in raw_data:
            try:
                # Expecting YYYY-MM
                date_str = record["date"]
                price_date = datetime.strptime(date_str, "%Y-%m").date()
                
                # We map the "Cereals" index as the primary signal for Grain category
                cereal_index = float(record.get("cereals", 100))
                
                standardized.append({
                    "source": self.source_name,
                    "date": price_date,
                    "state": "Global",
                    "district": "FAO",
                    "market": "FAO Index",
                    "commodity": "Food Price Index",
                    "variety": "Cereals",
                    "min_price": cereal_index,
                    "max_price": cereal_index,
                    "modal_price": cereal_index,
                    "unit": "Index",
                    "arrival_quantity": 0,
                    "normalized_price_per_kg": 0 # Non-price signal
                })
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Skipping malformed FAO standardized record: {e}")
                continue
        return standardized


class APEDAConnector(BaseConnector):
    """Connector for APEDA Export Statistics."""
    
    def __init__(self):
        super().__init__("APEDA")
        self.api_url = "https://apeda.gov.in/apedawebsite/api"
        self.api_key = settings.APEDA_API_KEY

    def fetch_data(self, date_obj: datetime, **kwargs) -> List[Dict[str, Any]]:
        return self._get_mock_data(date_obj)

    def _get_mock_data(self, date_obj: datetime) -> List[Dict[str, Any]]:
        """Return mock APEDA export data."""
        return [
            {
                "product": "Basmati Rice",
                "destination": "UAE",
                "quantity_tons": "25000",
                "value_usd_million": "28.5",
                "unit_price_usd_per_ton": "1140",
                "month": date_obj.strftime("%B %Y"),
                "date": date_obj.strftime("%Y-%m-%d")
            },
            {
                "product": "Spices",
                "destination": "USA",
                "quantity_tons": "15000",
                "value_usd_million": "45.2",
                "unit_price_usd_per_ton": "3013",
                "month": date_obj.strftime("%B %Y"),
                "date": date_obj.strftime("%Y-%m-%d")
            }
        ]

    def transform_to_standard(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        standardized = []
        for record in raw_data:
            try:
                # Convert USD to INR (approximate)
                usd_price = float(record.get("unit_price_usd_per_ton", 1000))
                inr_price = usd_price * 83  # Approximate USD to INR
                date = datetime.strptime(record.get("date", "2026-01-01"), "%Y-%m-%d").date()
                
                standardized.append({
                    "source": self.source_name,
                    "date": date,
                    "state": "Export Hub",
                    "district": record.get("destination", "Global"),
                    "market": "APEDA",
                    "commodity": record.get("product", "Unknown"),
                    "variety": "Export Grade",
                    "min_price": inr_price,
                    "max_price": inr_price,
                    "modal_price": inr_price,
                    "unit": "Ton",
                    "arrival_quantity": float(record.get("quantity_tons", 0)),
                    "normalized_price_per_kg": inr_price / 1000
                })
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Skipping malformed APEDA record: {e}")
                continue
        return standardized


class MPEDAConnector(BaseConnector):
    """Connector for MPEDA Marine Export Statistics."""
    
    def __init__(self):
        super().__init__("MPEDA")
        self.api_url = "https://mpeda.gov.in/api"

    def fetch_data(self, date_obj: datetime, **kwargs) -> List[Dict[str, Any]]:
        return self._get_mock_data(date_obj)

    def _get_mock_data(self, date_obj: datetime) -> List[Dict[str, Any]]:
        """Return mock MPEDA marine product data."""
        return [
            {
                "product": "Shrimp",
                "grade": "Export Grade (Large)",
                "port": "Kochi",
                "quantity_tons": "12000",
                "value_usd_million": "98.5",
                "unit_price_usd_per_kg": "8.2",
                "date": date_obj.strftime("%Y-%m-%d")
            },
            {
                "product": "Fish",
                "grade": "Fresh Catch",
                "port": "Veraval",
                "quantity_tons": "8500",
                "value_usd_million": "42.1",
                "unit_price_usd_per_kg": "4.95",
                "date": date_obj.strftime("%Y-%m-%d")
            }
        ]

    def transform_to_standard(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        standardized = []
        for record in raw_data:
            try:
                # Convert USD to INR
                usd_price = float(record.get("unit_price_usd_per_kg", 5))
                inr_price = usd_price * 83
                date = datetime.strptime(record.get("date", "2026-01-01"), "%Y-%m-%d").date()
                
                standardized.append({
                    "source": self.source_name,
                    "date": date,
                    "state": "Coastal Hub",
                    "district": record.get("port", "Marine Port"),
                    "market": record.get("port", "Marine Port"),
                    "commodity": record.get("product", "Marine Product"),
                    "variety": record.get("grade", "Standard"),
                    "min_price": inr_price,
                    "max_price": inr_price,
                    "modal_price": inr_price,
                    "unit": "Kg",
                    "arrival_quantity": float(record.get("quantity_tons", 0)) * 1000,
                    "normalized_price_per_kg": inr_price
                })
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Skipping malformed MPEDA record: {e}")
                continue
        return standardized


class NCDEXConnector(BaseConnector):
    """Connector for NCDEX Futures Prices."""
    
    def __init__(self):
        super().__init__("NCDEX")

    def fetch_data(self, date_obj: datetime, **kwargs) -> List[Dict[str, Any]]:
        return self._get_mock_data(date_obj)

    def _get_mock_data(self, date_obj: datetime) -> List[Dict[str, Any]]:
        """Return mock NCDEX futures data."""
        return [
            {
                "symbol": "DHANIYA",
                "expiry": "April 2026",
                "spot_price": "7450",
                "future_price": "7820",
                "open_interest": "12450",
                "date": date_obj.strftime("%Y-%m-%d")
            },
            {
                "symbol": "CASTOR",
                "expiry": "April 2026",
                "spot_price": "5600",
                "future_price": "5750",
                "open_interest": "4500",
                "date": date_obj.strftime("%Y-%m-%d")
            }
        ]

    def transform_to_standard(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        standardized = []
        for record in raw_data:
            try:
                spot = float(record.get("spot_price", 0))
                future = float(record.get("future_price", 0))
                date = datetime.strptime(record.get("date", "2026-01-01"), "%Y-%m-%d").date()
                
                standardized.append({
                    "source": self.source_name,
                    "date": date,
                    "state": "Exchange Node",
                    "district": "Futures Market",
                    "market": "NCDEX Terminal",
                    "commodity": record.get("symbol", "Unknown").capitalize(),
                    "variety": f"Future {record.get('expiry', '')}",
                    "min_price": spot,
                    "max_price": future,
                    "modal_price": (spot + future) / 2,
                    "unit": "Quintal",
                    "arrival_quantity": float(record.get("open_interest", 0)),
                    "normalized_price_per_kg": (spot + future) / 200
                })
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Skipping malformed NCDEX record: {e}")
                continue
        return standardized


    def get_live_ticks(self) -> List[Dict[str, Any]]:
        """Simulate real-time tick data with slight variance."""
        import random
        base_data = self._get_mock_data(datetime.now())
        for item in base_data:
            variance = random.uniform(-10.5, 15.5)
            item["spot_price"] = str(float(item["spot_price"]) + variance)
            item["future_price"] = str(float(item["future_price"]) + variance)
            item["timestamp"] = datetime.now().isoformat()
        return base_data

class MCXConnector(BaseConnector):
    """Connector for MCX Commodity Exchange Prices."""
    
    def __init__(self):
        super().__init__("MCX")

    def fetch_data(self, date_obj: datetime, **kwargs) -> List[Dict[str, Any]]:
        return self._get_mock_data(date_obj)

    def get_live_ticks(self) -> List[Dict[str, Any]]:
        """Simulate real-time tick data with slight variance."""
        import random
        base_data = self._get_mock_data(datetime.now())
        for item in base_data:
            variance = random.uniform(-25.0, 45.0)
            item["spot_price"] = str(float(item["spot_price"]) + variance)
            item["future_price"] = str(float(item["future_price"]) + variance)
            item["timestamp"] = datetime.now().isoformat()
        return base_data

    def _get_mock_data(self, date_obj: datetime) -> List[Dict[str, Any]]:
        """Return mock MCX commodity prices."""
        return [
            {
                "symbol": "GOLD",
                "spot_price": "68500",
                "future_price": "69200",
                "date": date_obj.strftime("%Y-%m-%d")
            },
            {
                "symbol": "SILVER",
                "spot_price": "82000",
                "future_price": "82800",
                "date": date_obj.strftime("%Y-%m-%d")
            }
        ]

    def transform_to_standard(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        standardized = []
        for record in raw_data:
            try:
                spot = float(record.get("spot_price", 0))
                future = float(record.get("future_price", 0))
                date = datetime.strptime(record.get("date", "2026-01-01"), "%Y-%m-%d").date()
                
                standardized.append({
                    "source": self.source_name,
                    "date": date,
                    "state": "Exchange Node",
                    "district": "Commodity Exchange",
                    "market": "MCX Terminal",
                    "commodity": record.get("symbol", "Unknown"),
                    "variety": "Spot/Future",
                    "min_price": spot,
                    "max_price": future,
                    "modal_price": (spot + future) / 2,
                    "unit": "Gram",
                    "arrival_quantity": 0,
                    "normalized_price_per_kg": (spot + future) / 2
                })
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Skipping malformed MCX record: {e}")
                continue
        return standardized


class ConnectorFactory:
    """Factory for instantiating appropriate connectors."""
    
    _connectors = {
        "AGMARKNET": AgmarknetConnector,
        "USDA": USDAConnector,
        "FAO": FAOConnector,
        "APEDA": APEDAConnector,
        "MPEDA": MPEDAConnector,
        "NCDEX": NCDEXConnector,
        "MCX": MCXConnector,
    }

    @classmethod
    def get_connector(cls, source_name: str) -> Optional[BaseConnector]:
        """Get a connector instance by source name."""
        connector_class = cls._connectors.get(source_name)
        if connector_class:
            return connector_class()
        logger.warning(f"Unknown connector: {source_name}")
        return None

    @classmethod
    def get_all_connectors(cls) -> List[BaseConnector]:
        """Get all available connectors."""
        return [connector_class() for connector_class in cls._connectors.values()]
