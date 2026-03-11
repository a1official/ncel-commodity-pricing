import sys
import os
from sqlalchemy import create_engine
from .models.models import Base
from .core.config_enhanced import settings

def init_db():
    print(f"Initializing database at: {settings.DATABASE_URL}")
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")

if __name__ == "__main__":
    init_db()
