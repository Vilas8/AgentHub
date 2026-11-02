# AgentHub — AI Agent Marketplace

AgentHub is a production-grade AI Agent Marketplace where individuals, businesses, and developers discover, use, build, and monetize AI agents.

## Quick Start

### Prerequisites

- Node.js 22+
- Python 3.12+
- PostgreSQL 16+ (or use SQLite for local dev)
- Redis 7+

### 1. Clone and set up environment

```bash
cp .env.example .env
# Edit .env with your values
```

### 2. Start the backend

```bash
cd apps/api
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 3. Start the frontend

```bash
cd apps/web
npm install
npm run dev
```

### 4. Start the execution worker

```bash
cd apps/api
python -m workers.execution.worker
```

## Architecture

See [docs/architecture/ADR.md](docs/architecture/ADR.md).

## Documentation

- [Development Setup](docs/development/ENVIRONMENT.md)
- [API Reference](docs/api/)
- [Database Schema](docs/database/)
- [Deployment Guide](docs/deployment/)
- [Security](docs/security/)
- [Build Progress](docs/BUILD_PROGRESS.md)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | Python, FastAPI, Pydantic v2 |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic |
| Database | PostgreSQL 16 |
| Cache/Queue | Redis 7 |
| Agent Orchestration | LangGraph |
| Storage | S3-compatible (MinIO for dev) |

## License

Proprietary. All rights reserved.
