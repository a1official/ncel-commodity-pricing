# Frontend Performance Day 4

## Objective
Reduce payload size and client work by splitting heavy data requests into purpose-built APIs and enforcing strict pagination.

## Implemented Backend Contracts
- `GET /prices/page`
  - Returns `{ items, pagination }`
  - Enforces `limit <= 300`
  - Includes `total`, `returned`, and `has_more`
- `GET /prices/summary`
  - Returns KPI-ready aggregates:
  - `record_count`, `avg_price_per_kg`, `total_arrival_quantity`, `unique_markets`, `latest_date`, `latest_avg_price_per_kg`, `seven_day_change_pct`
- `GET /prices/timeseries`
  - Returns daily server-side aggregates:
  - `date`, `avg_modal_price`, `total_arrival_quantity`, `observations`

## Indexing
- Added startup index creation in backend lifespan:
  - `price_records(date)`
  - `price_records(commodity_id, date)`
  - `price_records(market_id, date)`
  - `price_records(source_id, date)`
  - `commodities(category)`

## Frontend Changes
- Dashboard now consumes sliced endpoints:
  - list/table via `/prices/page`
  - top KPI cards via `/prices/summary`
  - charts via `/prices/timeseries`
- Marine page request reduced from `limit=1000` to `limit=300`.

## Expected Impact
- Smaller payloads per request
- Faster first render on heavy routes
- Less browser aggregation work
- Better scaling under broad filters
