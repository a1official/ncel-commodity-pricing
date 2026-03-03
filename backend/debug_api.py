import sys
import os
sys.path.append(os.getcwd())
from app.api.v1.endpoints import get_markets
from app.core.database import SessionLocal
import json

db = SessionLocal()
try:
    markets = get_markets(db)
    print(f"Fetched {len(markets)} markets")
    # print(json.dumps([m.__dict__ for m in markets[:2]], default=str)) # m.__dict__ might have extra stuff
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.close()
