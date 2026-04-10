from __future__ import annotations

import argparse
import json
from datetime import datetime

from app.core.database import SessionLocal
from app.services.daily_price_sync import DailyAgmarknetSyncService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch today's AGMARKNET prices and upsert them into the local warehouse.")
    parser.add_argument("--date", help="Override sync date in YYYY-MM-DD format. Defaults to today.")
    parser.add_argument("--allow-mock-fallback", action="store_true", help="Allow connector mock data when API keys are unavailable.")
    parser.add_argument("--dry-run", action="store_true", help="Run the sync without committing DB changes.")
    parser.add_argument("--page-size", type=int, default=100, help="AGMARKNET page size per request.")
    parser.add_argument("--max-pages", type=int, default=200, help="Maximum pages to fetch per commodity filter.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sync_datetime = datetime.strptime(args.date, "%Y-%m-%d") if args.date else datetime.now()

    db = SessionLocal()
    try:
        service = DailyAgmarknetSyncService(db)
        result = service.run(
            sync_datetime,
            allow_mock_fallback=args.allow_mock_fallback,
            dry_run=args.dry_run,
            page_size=args.page_size,
            max_pages=args.max_pages,
        )
        print(json.dumps(result, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
