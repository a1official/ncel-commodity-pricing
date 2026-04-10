from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .config_enhanced import settings

engine = create_engine(settings.sync_database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def ensure_performance_indexes() -> None:
    """Create commonly used query indexes if they do not already exist."""
    statements = [
        "CREATE INDEX IF NOT EXISTS idx_price_records_date ON price_records(date)",
        "CREATE INDEX IF NOT EXISTS idx_price_records_commodity_date ON price_records(commodity_id, date)",
        "CREATE INDEX IF NOT EXISTS idx_price_records_market_date ON price_records(market_id, date)",
        "CREATE INDEX IF NOT EXISTS idx_price_records_source_date ON price_records(source_id, date)",
        "CREATE INDEX IF NOT EXISTS idx_commodities_category ON commodities(category)",
    ]

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
