# Commodity Price Intelligence Platform Architecture

## System Overview
A scalable, commodity-agnostic platform designed for Indian agricultural and marine price intelligence.

## 1. High-Level Architecture
- **Connector Layer**: Modular Python classes for each data source (AGMARKNET, eNAM, etc.).
- **Orchestration Layer**: Manages ingestion schedules and job triggering (Prefect/Airflow ready).
- **Data Lake (Raw)**: S3-compatible storage for raw JSON responses (partitioned by source/date).
- **Processing Layer (Normalization Engine)**:
    - Standardizes commodity/variety names using fuzzy matching & embeddings.
    - Normalizes units (Quintal/Kg/Ton -> Standard metric).
    - Deduplicates markets/mandis.
- **Data Warehouse**: PostgreSQL database with a normalized schema for high-performance queries.
- **API Layer**: FastAPI providing REST endpoints for analytics and data access.
- **Frontend**: Next.js dashboard with interactive maps and charts.

## 2. Data Model (PostgreSQL)

### Master Entities
- `commodities`: id, name, category (grain, spice, etc.)
- `varieties`: id, commodity_id, name, aliases (JSONB)
- `states`: id, name
- `districts`: id, state_id, name
- `markets`: id, district_id, name, lat, lon
- `sources`: id, name, type (Govt, Scraping, Private)

### Transactional Data
- `price_records`:
    - id (UUID)
    - date (Date)
    - commodity_id
    - variety_id
    - market_id
    - source_id
    - min_price (Decimal)
    - max_price (Decimal)
    - modal_price (Decimal)
    - arrival_quantity (Decimal)
    - unit (Enum: KG, QUINTAL, TON)
    - normalized_price_per_kg (Decimal) - *Calculated for indexing*
    - created_at (Timestamp)

## 3. Normalization Logic
- **Fuzzy Mapping**: Uses `RapidFuzz` or `SentenceTransformers` to map variations like "Paddy (Dhan)" and "Paddy" to the same master variety.
- **Unit Conversion**: Logic to handle `1 Quintal = 100 Kg`, `1 Ton = 1000 Kg`.

## 4. Ingestion Pipeline
1. **Extract**: Connectors fetch data and save to `raw/`.
2. **Transform**: Normalization engine processes raw data.
3. **Load**: Upsert into PostgreSQL.

## 5. Technology Stack
- **Backend**: FastAPI, SQLAlchemy (Postgres), Pydantic.
- **Frontend**: Next.js, Tailwind CSS, Recharts, Lucide Icons.
- **Storage**: PostgreSQL (TimescaleDB extension optional for time-series).
- **Cache**: Redis (for API caching).
- **Tooling**: Docker, Pytest.
