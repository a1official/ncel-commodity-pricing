from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Commodity Price Intelligence Platform"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "ncel_commodity"
    DATABASE_URL: Optional[str] = None
    DATA_GOV_API_KEY: Optional[str] = None

    @property
    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        # Default to local SQLite for easier local development
        return "sqlite:///./ncel_local.db"

    class Config:
        case_sensitive = True

settings = Settings()
