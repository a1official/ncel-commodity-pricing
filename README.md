# NCEL Commodity Price Intelligence Platform

NCEL is a commodity intelligence platform with a Next.js frontend, a FastAPI backend, and an AWS Lambda ingestion pipeline for agricultural and marine price data.

## Overview

The project currently supports:

- live commodity and market dashboards
- a live weather and geospatial page at `/geospatial`
- multi-source ingestion and normalization
- DynamoDB-based warehouse storage for Lambda ingestion
- frontend terminal views that are now wired to backend data instead of hardcoded arrays

## Main Components

### Frontend

- Framework: Next.js 14
- Location: [frontend](frontend)
- Key pages:
  - `/analytics/terminal`
  - `/geospatial`
  - `/marine`
  - `/markets`

### Backend

- Framework: FastAPI
- Location: [backend](backend)
- Key responsibilities:
  - API endpoints
  - analytics summaries
  - forecasting hooks
  - ingestion connectors
  - SQL-backed app services

### Lambda Ingestion

- Location: [backend/lambda_ingestion](backend/lambda_ingestion)
- Deployment helpers: [backend/lambda_deployment](backend/lambda_deployment)
- Current Lambda functions:
  - `get-price`
  - `update-attributes`
  - `ncel-orchestrator-ingestion`

## Data Flow

The active ingestion flow is:

1. Source API/site is called
2. Data is fetched in source-specific format
3. Records are normalized into the NCEL schema
4. Normalized rows are written to DynamoDB
5. Backend and frontend consume the processed data

For scheduled cloud ingestion, the intended flow is:

1. EventBridge triggers `ncel-orchestrator-ingestion`
2. Orchestrator runs source fetches
3. Data is normalized
4. Data is stored in DynamoDB

At the moment, manual Lambda invocation works. EventBridge scheduling still depends on AWS EventBridge permissions in the target account.

## Sources

The ingestion code currently targets these sources:

- AGMARKNET
- USDA
- FAO
- FMPIS
- MPEDA

### Commodity Coverage

The AGMARKNET connector is currently configured to target:

- Rice
  - Basmati
  - non-basmati / common rice aliases
- Spices
  - Cumin
  - Turmeric
  - Chilli
- Fruits and vegetables
  - Grapes
  - Potato
  - Banana
  - Onion
  - Tomato
  - Pineapple
- Millets
  - Bajra
  - Jowar
  - Ragi
  - Kodo millet
  - Foxtail millet
  - Little millet
  - Proso millet
  - Barnyard millet
- Groundnut
- Maize

Marine coverage comes from:

- FMPIS
- MPEDA

## Normalized Schema

The Lambda ingestion normalizes records into this business schema:

```text
state
district
market
commodity
variety
date
min_price
max_price
modal_price
unit
arrival_quantity
source
```

### DynamoDB Item Shape

The DynamoDB warehouse also stores internal index fields:

```text
pk
sk
gsi1pk
gsi1sk
execution_id
source
date
state
district
market
commodity
variety
unit
min_price
max_price
modal_price
arrival_quantity
normalized_price_per_kg
ingested_at
```

## Geospatial Page

The `/geospatial` page currently includes:

- satellite basemap
- live weather data
- live radar overlay
- map click lookup
- area search
- auto-refresh
- timestamped updates

Live data providers currently used there:

- Open-Meteo
- RainViewer

## Terminal Page

The `/analytics/terminal` page has been updated to use backend data instead of hardcoded dashboard arrays.

Backend route used:

- `/api/v1/analytics/terminal-summary`

Current behavior:

- fetches live backend summary data for the selected commodity and aliases
- falls back gracefully if a selected commodity has no current rows

## Local Development

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:

- `http://localhost:3000`

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend URL:

- `http://localhost:8000`
- docs: `http://localhost:8000/docs`

## Environment Variables

### Frontend

Use [frontend/.env.local](frontend/.env.local):

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend

Use [backend/.env](backend/.env).

Important keys include:

```env
DATABASE_URL=sqlite:///./ncel_local.db
CORS_ORIGINS=http://localhost:3000
DATA_GOV_API_KEY=...
USDA_API_KEY=...
GROQ_API_KEY=...
SARVAM_API_KEY=...
```

### Lambda Deployment

Use [backend/lambda_deployment/.env](backend/lambda_deployment/.env) for AWS deployment settings.

## Lambda Deployment Notes

The project includes a ZIP + Layers Lambda deployment path.

Important files:

- [backend/lambda_deployment/deploy.ps1](backend/lambda_deployment/deploy.ps1)
- [backend/lambda_deployment/configure_schedules.ps1](backend/lambda_deployment/configure_schedules.ps1)
- [backend/lambda_ingestion/deploy_zip_lambdas.ps1](backend/lambda_ingestion/deploy_zip_lambdas.ps1)

Current AGMARKNET throttling defaults are intentionally conservative:

- `AGMARKNET_PAGE_SIZE=25`
- `AGMARKNET_MAX_PAGES=2`
- `AGMARKNET_PAGE_DELAY_SECONDS=2.0`
- `AGMARKNET_FILTER_DELAY_SECONDS=3.0`

This is to reduce the risk of API blocking.

## Current Status

Working:

- direct AGMARKNET API key validation
- Lambda fetch and normalize flow
- Lambda write to DynamoDB
- latest-only filtering in Lambda fetch flow
- geospatial weather page
- terminal page live backend wiring

Partially dependent on AWS account permissions:

- EventBridge schedule creation
- fully automated scheduled ingestion in AWS

## Repository Structure

```text
ncel-commodity-pricing/
|-- backend/
|   |-- app/
|   |   |-- api/
|   |   |-- core/
|   |   |-- ingestion/
|   |   |-- models/
|   |   `-- services/
|   |-- lambda_deployment/
|   `-- lambda_ingestion/
|-- docs/
`-- frontend/
    `-- src/
```

## Notes

- Local app APIs currently use SQL-backed backend models.
- Lambda ingestion currently writes to DynamoDB.
- If you want the app UI to read warehouse data directly, add a DynamoDB-backed backend aggregation layer or sync warehouse rows into SQL tables used by the frontend APIs.
