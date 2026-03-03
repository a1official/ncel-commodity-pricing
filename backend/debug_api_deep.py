import sys
import os
sys.path.append(os.getcwd())
from app.api.v1.endpoints import get_markets
from app.core.database import SessionLocal
from pydantic import RootModel
from app.schemas import schemas
import json

db = SessionLocal()
try:
    markets = get_markets(db)
    print(f"Fetched {len(markets)} markets")
    dataset = [schemas.Market.model_validate(m).model_dump() for m in markets]
    print(json.dumps(dataset, default=str))
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.close()
