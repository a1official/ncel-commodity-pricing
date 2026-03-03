import sys
import os
from sqlalchemy import create_engine
from .models.models import Base
from .core.config import settings

def init_db():
    print(f"Initializing database at: {settings.get_database_url}")
    engine = create_engine(settings.get_database_url)
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")

if __name__ == "__main__":
    init_db()
