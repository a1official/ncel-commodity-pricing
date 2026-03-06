"""
Enhanced Configuration Management
Loads settings from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # ========================================================================
    # PROJECT CONFIGURATION
    # ========================================================================
    PROJECT_NAME: str = "NCEL Commodity Intelligence Platform"
    PROJECT_VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    
    # ========================================================================
    # DATABASE CONFIGURATION
    # ========================================================================
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/commodity_db"
    SQLALCHEMY_ECHO: bool = False
    
    # ========================================================================
    # API KEYS - DATA SOURCES
    # ========================================================================
    DATA_GOV_API_KEY: Optional[str] = None
    USDA_API_KEY: Optional[str] = None
    FAO_API_KEY: Optional[str] = None
    APEDA_API_KEY: Optional[str] = None
    MPEDA_API_KEY: Optional[str] = None
    
    # ========================================================================
    # REDIS CONFIGURATION (Optional)
    # ========================================================================
    REDIS_URL: Optional[str] = None
    REDIS_CACHE_ENABLED: bool = False
    REDIS_CACHE_TTL: int = 3600  # 1 hour
    
    # ========================================================================
    # CORS CONFIGURATION
    # ========================================================================
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:5173"
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # ========================================================================
    # FORECASTING CONFIGURATION
    # ========================================================================
    FORECAST_LOOKBACK_WEEKS: int = 52
    FORECAST_CONFIDENCE_THRESHOLD: float = 70.0
    FORECAST_MAX_WEEKS: int = 12
    FORECAST_DEFAULT_WEEKS: int = 6
    
    # ========================================================================
    # LSTM CONFIGURATION
    # ========================================================================
    LSTM_SEQUENCE_LENGTH: int = 4
    LSTM_EPOCHS: int = 20
    LSTM_BATCH_SIZE: int = 4
    LSTM_DROPOUT: float = 0.2
    LSTM_UNITS: List[int] = [64, 32]
    
    # ========================================================================
    # XGBOOST CONFIGURATION
    # ========================================================================
    XGBOOST_N_ESTIMATORS: int = 100
    XGBOOST_MAX_DEPTH: int = 5
    XGBOOST_LEARNING_RATE: float = 0.1
    XGBOOST_SUBSAMPLE: float = 0.8
    XGBOOST_COLSAMPLE_BYTREE: float = 0.8
    
    # ========================================================================
    # PREFECT CONFIGURATION
    # ========================================================================
    PREFECT_API_URL: Optional[str] = None
    PREFECT_HOME: str = os.path.expanduser("~/.prefect")
    PREFECT_ENABLED: bool = True
    
    # ========================================================================
    # INGESTION CONFIGURATION
    # ========================================================================
    INGESTION_BATCH_SIZE: int = 500
    INGESTION_TIMEOUT: int = 30
    INGESTION_RETRIES: int = 2
    INGESTION_RETRY_DELAY: int = 60
    
    # ========================================================================
    # LOGGING CONFIGURATION
    # ========================================================================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # ========================================================================
    # COMMODITY CONFIGURATION
    # ========================================================================
    SUPPORTED_COMMODITIES: List[str] = [
        # Grains
        "Rice", "Wheat", "Maize", "Millets",
        # Spices
        "Turmeric", "Chilli", "Cumin",
        # Vegetables
        "Onion", "Tomato", "Potato",
        # Fruits
        "Banana", "Grapes", "Pineapple",
        # Marine
        "Shrimp", "Mackerel", "Tuna", "Trout",
        # Cash Crops
        "Soybean", "Sugar", "Cotton", "Groundnut"
    ]
    
    COMMODITY_CATEGORIES: dict = {
        "Grain": ["Rice", "Wheat", "Maize", "Millets"],
        "Spice": ["Turmeric", "Chilli", "Cumin"],
        "Vegetable": ["Onion", "Tomato", "Potato"],
        "Fruit": ["Banana", "Grapes", "Pineapple"],
        "Marine": ["Shrimp", "Mackerel", "Tuna", "Trout"],
        "Cash Crop": ["Soybean", "Sugar", "Cotton", "Groundnut"]
    }
    
    # ========================================================================
    # DATA SOURCE CONFIGURATION
    # ========================================================================
    AVAILABLE_SOURCES: List[str] = [
        "AGMARKNET",
        "USDA",
        "FAO",
        "APEDA",
        "MPEDA",
        "NCDEX",
        "MCX"
    ]
    
    SOURCE_TYPES: dict = {
        "AGMARKNET": "Government",
        "USDA": "Government",
        "FAO": "Government",
        "APEDA": "Government",
        "MPEDA": "Government",
        "NCDEX": "Market",
        "MCX": "Market"
    }
    
    # ========================================================================
    # PAGINATION CONFIGURATION
    # ========================================================================
    DEFAULT_PAGE_SIZE: int = 100
    MAX_PAGE_SIZE: int = 1000
    
    # ========================================================================
    # CACHE CONFIGURATION
    # ========================================================================
    CACHE_ENABLED: bool = True
    CACHE_TTL_PRICES: int = 3600  # 1 hour
    CACHE_TTL_FORECASTS: int = 1800  # 30 minutes
    CACHE_TTL_MARKETS: int = 86400  # 1 day
    
    # ========================================================================
    # FEATURE FLAGS
    # ========================================================================
    FEATURE_ENSEMBLE_FORECASTING: bool = True
    FEATURE_PREFECT_PIPELINE: bool = True
    FEATURE_SOURCE_FILTERING: bool = True
    FEATURE_ADVANCED_ANALYTICS: bool = True
    FEATURE_SUPPLY_RISK_ASSESSMENT: bool = True
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings


def validate_api_keys() -> dict:
    """Validate that required API keys are configured."""
    validation_result = {
        "valid": True,
        "warnings": [],
        "errors": []
    }
    
    # Check for at least one API key
    if not any([
        settings.DATA_GOV_API_KEY,
        settings.USDA_API_KEY,
        settings.FAO_API_KEY,
        settings.APEDA_API_KEY,
        settings.MPEDA_API_KEY
    ]):
        validation_result["warnings"].append(
            "No API keys configured. System will use mock data for demo purposes."
        )
    
    # Check database connection
    if not settings.DATABASE_URL:
        validation_result["valid"] = False
        validation_result["errors"].append("DATABASE_URL not configured")
    
    return validation_result


def get_commodity_category(commodity_name: str) -> str:
    """Get the category of a commodity."""
    for category, commodities in settings.COMMODITY_CATEGORIES.items():
        if commodity_name in commodities:
            return category
    return "Other"


def is_commodity_supported(commodity_name: str) -> bool:
    """Check if a commodity is in the supported list."""
    return commodity_name in settings.SUPPORTED_COMMODITIES


def get_source_type(source_name: str) -> str:
    """Get the type of a data source."""
    return settings.SOURCE_TYPES.get(source_name, "Unknown")


# Validate on import
validation = validate_api_keys()
if validation["errors"]:
    import sys
    print("Configuration Errors:")
    for error in validation["errors"]:
        print(f"  - {error}")
    sys.exit(1)

if validation["warnings"]:
    import logging
    logger = logging.getLogger(__name__)
    for warning in validation["warnings"]:
        logger.warning(warning)
