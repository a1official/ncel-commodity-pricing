from app.core.database import SessionLocal
from app.models.models import State

db = SessionLocal()
coastal = [
    'Andhra Pradesh', 'Goa', 'Gujarat', 'Karnataka', 'Kerala', 
    'Maharashtra', 'Odisha', 'Tamil Nadu', 'West Bengal'
]

for s_name in coastal:
    state = db.query(State).filter_by(name=s_name).first()
    if not state:
        print(f"Adding state: {s_name}")
        db.add(State(name=s_name))
        db.commit()
    else:
        print(f"State exists: {s_name}")

db.close()
