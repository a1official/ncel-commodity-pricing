# NCEL Commodity Price Intelligence Platform

A production-grade, scalable platform for tracking agricultural and marine commodity prices across India.

## 🚀 Key Features

- **AI Voice Assistant**: Native voice-to-voice communication using Groq (STT/Whisper) and Sarvam AI Bulbul (v3 TTS).
- **Persistent Chat Memory**: Local conversation history using IndexedDB, providing persistence across browser refreshes.
- **Dynamic Language Support**: Real-time translation and voice output across 7+ regional Indian languages.
- **Commodity Agnostic**: Onboard new commodities via metadata/connectors without core code changes.
- **Normalization Engine**: Standardizes units, maps variety aliases using fuzzy matching, and deduplicates markets.
- **Pluggable Connectors**: Modular architecture for Agmarknet, eNAM, NFDB, and state mandi boards.
- **Modern Analytics**: Next.js dashboard with historical trends, heatmaps, and arrival vs price analysis.

## 🛠 Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Groq SDK, Sarvam AI API.
- **Data Engineering**: RapidFuzz (Normalization), Requests/BS4 (Ingestion).
- **Frontend**: Next.js 14, Tailwind CSS, Recharts, Framer Motion, IndexedDB.
- **Deployment**: Docker, Docker Compose.

## 🏃 Getting Started

### 1. Environment Variables
Create a `.env` file in both `root` and `backend/` directories with your API keys:
```env
GROQ_API_KEY=your_groq_api_key_here
SARVAM_API_KEY=your_sarvam_api_key_here
```

### 2. Prerequisites
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
