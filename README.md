# Smart Greenhouse

A three-tier greenhouse monitoring app: FastAPI backend, PostgreSQL database, React + TypeScript frontend.

## Prerequisites
- Python 3.11+
- Node.js 20 LTS
- Docker Desktop

## First-time setup

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Start the database
docker compose up -d

# 3. Install backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 4. Run Alembic baseline
alembic upgrade head

# 5. Install frontend
cd ../frontend
npm install
```

## Daily start

**Terminal 1 — Database:**
```bash
docker compose up -d
```

**Terminal 2 — Backend:**
```bash
cd backend
source .venv/bin/activate
PYTHONPATH=src uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 3 — Frontend:**
```bash
cd frontend
npm run dev
```

## URLs

| Service | URL |
|---|---|
| UI | http://localhost:5173 |
| Dashboard | http://localhost:5173/dashboard |
| Health check | http://localhost:8000/health |
| API docs (Scalar) | http://localhost:8000/scalar |
| OpenAPI schema | http://localhost:8000/openapi.json |

## Phases
See [docs/phases/README.md](docs/phases/README.md) for phase order.