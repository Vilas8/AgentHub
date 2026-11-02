# Development Environment Setup

## Prerequisites

| Tool | Minimum Version | Install |
|------|----------------|---------|
| Node.js | 22.x | https://nodejs.org |
| Python | 3.12 | https://python.org |
| PostgreSQL | 16 | https://postgresql.org |
| Redis | 7 | https://redis.io |
| Git | 2.x | https://git-scm.com |

## Optional (for full feature set)

- MinIO (S3-compatible storage): `docker run -p 9000:9000 minio/minio server /data`
- Docker (for containerized dev)

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Minimum required for local dev:
- `SECRET_KEY` — any 32+ char random string
- `JWT_SECRET_KEY` — any 32+ char random string
- `DATABASE_URL` — SQLite or PostgreSQL URL
- At least one AI provider key (GEMINI_API_KEY or OPENAI_API_KEY)

## Backend Setup

```bash
cd apps/api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

## Frontend Setup

```bash
cd apps/web
npm install
npm run dev
```

App available at: http://localhost:3000

## Running Tests

```bash
# Backend
cd apps/api
pytest tests/ -v --cov=app

# Frontend
cd apps/web
npm test
```
