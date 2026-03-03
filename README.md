# NCEL Commodity Price Intelligence Platform

A production-grade, scalable platform for tracking agricultural and marine commodity prices across India.

## 🚀 Key Features

- **Commodity Agnostic**: Onboard new commodities via metadata/connectors without core code changes.
- **Normalization Engine**: Standardizes units, maps variety aliases using fuzzy matching, and deduplicates markets.
- **Pluggable Connectors**: Modular architecture for Agmarknet, eNAM, NFDB, and state mandi boards.
- **Modern Analytics**: Next.js dashboard with historical trends, heatmaps, and arrival vs price analysis.
- **Scalable Architecture**: Containerized with Docker, PostgreSQL for persistence, and FastAPI for real-time access.

## 🛠 Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, PostgreSQL.
- **Data Engineering**: RapidFuzz (Normalization), Requests/BS4 (Ingestion).
- **Frontend**: Next.js 14, Tailwind CSS, Recharts, Framer Motion.
- **Deployment**: Docker, Docker Compose.

## 🏃 Getting Started

### 1. Prerequisites
- Docker & Docker Compose
- Node.js (for local frontend development)
- Python 3.11 (for local backend development)

### 2. Run with Docker
```bash
docker-compose up --build
```
This will start:
- **PostgreSQL**: `localhost:5432`
- **FastAPI Backend**: `localhost:8000`
- **Frontend Dashboard**: `localhost:3000` (Add frontend to compose if preferred)

### 3. Local Development

#### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

#### Ingestion Job
To run a sample ingestion (Agmarknet):
```bash
cd backend
export PYTHONPATH=$PYTHONPATH:.
python -m app.ingestion.orchestrator
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## 📂 Project Structure

- `/backend`: Core API and services.
  - `/app/ingestion`: Data collection and standardization logic.
  - `/app/models`: Database schema definitions.
  - `/app/services`: Business logic (Normalization, Math).
- `/frontend`: Next.js dashboard application.
- `/docker-compose.yml`: Multi-container orchestration.

## 📄 License
Production-grade open-source license.
