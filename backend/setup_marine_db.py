from app.core.database import engine, SessionLocal
from app.models import models
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_marine_db():
    db = SessionLocal()
    try:
        # 1.1 Ensure Marine Category Support
        logger.info("Adding category column to commodities if not exists...")
        with engine.connect() as conn:
            # Check if category column exists
            result = conn.execute(text("PRAGMA table_info(commodities)"))
            columns = [row[1] for row in result]
            if 'category' not in columns:
                conn.execute(text("ALTER TABLE commodities ADD COLUMN category VARCHAR(50) DEFAULT 'Other'"))
                conn.commit()
                logger.info("Category column added.")
            else:
                logger.info("Category column already exists.")

            # Update existing marine commodities
            marine_species = ['Shrimp', 'Mackerel', 'Tuna', 'Trout', 'Fish', 'Catla', 'Rohu', 'Hilsa shad', 'Pangas catfish', 'Tilapia', 'Mrigal']
            placeholders = ', '.join([f"'{s}'" for s in marine_species])
            conn.execute(text(f"UPDATE commodities SET category = 'Marine Products' WHERE name IN ({placeholders})"))
            conn.commit()
            logger.info("Updated existing marine commodities category.")

        # 1.2 Coastal States Setup
        coastal_states = [
            "Andhra Pradesh", "Goa", "Gujarat", "Karnataka", "Kerala", 
            "Maharashtra", "Odisha", "Tamil Nadu", "West Bengal"
        ]
        logger.info("Ensuring coastal states exist...")
        for state_name in coastal_states:
            state = db.query(models.State).filter(models.State.name == state_name).first()
            if not state:
                new_state = models.State(name=state_name)
                db.add(new_state)
                logger.info(f"Added state: {state_name}")
        db.commit()

        # 1.3 FMPIS Source Setup
        logger.info("Ensuring FMPIS source exists...")
        source = db.query(models.Source).filter(models.Source.name == 'FMPIS').first()
        if not source:
            new_source = models.Source(name='FMPIS', source_type='Government')
            db.add(new_source)
            logger.info("Added FMPIS source.")
        db.commit()

        logger.info("Database setup for marine system completed successfully.")

    except Exception as e:
        logger.error(f"Error during database setup: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    setup_marine_db()
