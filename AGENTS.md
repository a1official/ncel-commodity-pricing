# AGENTS.md - NCEL Commodity Pricing Development Guide

## Project Overview

Monorepo with **Next.js 14 frontend** and **FastAPI Python backend** for tracking agricultural and marine commodity prices across India.

## Directory Structure

```
ncel-commodity-pricing/
├── frontend/                 # Next.js 14 (React 18, TypeScript, Tailwind)
│   └── src/
│       ├── app/            # App Router pages
│       ├── components/     # React components
│       ├── lib/            # Utilities, API clients, config
│       ├── hooks/          # Custom React hooks
│       └── context/        # React context providers
├── backend/                 # FastAPI Python backend
│   └── app/
│       ├── api/            # API endpoints
│       ├── models/         # SQLAlchemy models
│       ├── services/       # Business logic
│       └── ingestion/      # Data collection pipelines
└── docker-compose.yml
```

---

## Build / Lint / Test Commands

### Frontend (Next.js)

```bash
cd frontend

# Install & run
npm install
npm run dev                # http://localhost:3000
npm run build              # Production build
npm run start              # Production server
npm run lint               # ESLint
```

### Backend (Python)

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run ingestion pipeline
export PYTHONPATH=$PYTHONPATH:.
python -m app.ingestion.orchestrator

# Testing
pytest tests/test_file.py::test_function_name -v
pytest tests/test_file.py::TestClass::test_method -v
pytest                     # Run all tests
```

### Docker

```bash
docker-compose up --build
```

---

## Code Style Guidelines

### TypeScript / React (Frontend)

**Imports**
- Use `@/` prefix for absolute imports (configured in tsconfig.json)
- Order: React/Next → external libs → internal components → types

**Formatting**
- 2-space indentation, single quotes, trailing commas
- Use Prettier defaults (Next.js)

**Types**
- Explicit types for function params/returns
- Interfaces for objects, types for unions/primitives

**Naming**
- Components: PascalCase (`IndiaMap.tsx`, `TopBar.tsx`)
- Hooks: camelCase with `use` prefix (`useLivePrices.ts`)
- Utilities: camelCase (`api.ts`, `db.ts`)
- Constants: UPPER_SNAKE_CASE

**Components**
- Use `"use client"` directive for client-side components
- Functional components with hooks
- Tailwind CSS with custom brand colors:
  - `brand-primary` (#4F46E5)
  - `brand-secondary` (#10B981)
  - `brand-accent` (#06B6D4)

**Error Handling**
- Always check `response.ok` in fetch calls
- Throw descriptive errors: `throw new Error('Failed to fetch commodities')`
- Use try/catch in async functions

**Tailwind CSS**
- Dark mode via `class` strategy
- Use `dark:` prefix for dark mode variants
- Custom shadows: `shadow-glass`, `shadow-premium`
- Custom fonts: `font-display` (Outfit), `font-body` (Inter)

---

### Python / FastAPI (Backend)

**Imports**
- Standard library → third-party → local application
- Use absolute imports from `app` package

**Formatting**
- 4-space indentation, follow PEP 8
- Max line length: 120 characters

**Types**
- Python type hints throughout
- Pydantic models for request/response validation

**Naming**
- Variables/functions: snake_case (`fetch_prices`, `commodity_list`)
- Classes: PascalCase (`NCDEXConnector`, `CommodityIngestion`)
- Constants: UPPER_SNAKE_CASE
- DB models: singular PascalCase (`Commodity`, `Market`)

**Error Handling**
- Use FastAPI's HTTPException for API errors
- Log errors with proper severity levels
- Wrap async operations in try/except

**Database**
- SQLAlchemy ORM with async support
- Follow model conventions: `id`, `created_at`, `updated_at`
- Use Alembic for migrations

---

## Environment Variables

### Frontend (.env.local)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend (.env)
```
GROQ_API_KEY=your_groq_api_key
SARVAM_API_KEY=your_sarvam_api_key
DATABASE_URL=sqlite:///./ncel_local.db
CORS_ORIGINS=http://localhost:3000
```

---

## Testing Strategy

- **Frontend**: No test framework configured (consider Jest/React Testing Library)
- **Backend**: pytest installed. Place tests in `backend/tests/`
- Run single test: `pytest backend/tests/test_file.py::test_function_name -v`

---

## Important Notes

1. **TypeScript strict mode disabled** in tsconfig.json (`"strict": false`)
2. **No ESLint/Prettier config** files - uses Next.js defaults
3. **SQLite database** for local dev, PostgreSQL for production
4. **WebSocket endpoints** for real-time market ticker updates
5. **Use Context7 for documentation**: Always use Context7 when library/API documentation, code generation, setup or configuration steps are needed without needing explicit user request
