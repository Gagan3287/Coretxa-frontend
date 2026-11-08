# Cortexa Backend API Engine

Multi-tenant knowledge base, document ingestion, embeddings, and bot management API service powering **Cortexa** — custom AI assistants trained on your documents.

> Note: The Cortexa frontend is maintained in its own dedicated repository ([Coretxa-frontend](https://github.com/Gagan3287/Coretxa-frontend)) and continuously deployed to Vercel at `https://cortexa-io.vercel.app`. This repository contains the standalone Python / FastAPI backend engine and worker services.

---

## Architecture Overview

```
cortexa-backend/
├── app/
│   ├── api/
│   │   ├── auth.py              # Tenant and Platform Admin JWT login, register, refresh, /me
│   │   ├── tenants.py           # Organization / Tenant provisioning routes
│   │   └── v1/
│   │       ├── bots.py          # Multi-bot management, widget token issuance & quotas
│   │       └── documents.py     # Document upload, chunk listing, versioning & deletion
│   ├── core/
│   │   ├── config.py            # Environment-driven settings (pydantic-settings)
│   │   ├── database.py          # tenant_session() and platform_session() RLS session handlers
│   │   ├── security.py          # Password hashing (bcrypt) and JWT encode/decode
│   │   ├── storage.py           # Async file storage abstraction for uploaded files
│   │   └── upload_validation.py # File type, mime, magic-byte, and size security checks
│   ├── models/                  # SQLAlchemy ORM models: Tenant, User, Bot, Document, Chunk, Query...
│   ├── schemas/                 # Pydantic validation models for requests and responses
│   ├── services/
│   │   ├── embedding.py         # Google Gemini embeddings with rate-limiting & per-bot keys
│   │   ├── parser.py            # PDF / text document parsing and tokenization
│   │   ├── provisioning.py      # Tenant, user, and schema initializers
│   │   └── retrieval.py         # Version-aware vector search foundation
│   ├── worker/
│   │   ├── ingestion.py         # Background document parser, chunker & embedder job
│   │   └── queue.py             # Redis / Arq queue connection & job dispatch
│   ├── deps.py                  # FastAPI dependency injection (JWT, tenant context, DB)
│   └── main.py                  # FastAPI application entrypoint with CORS & routers
├── alembic/                     # Database migrations (0001 through 0010)
├── scripts/                     # Operational diagnostics and queue inspection utilities
├── sql/                         # Reference RLS policies and DB scripts
├── tests/                       # Comprehensive test suite (tenant isolation, RLS, API, embeddings)
├── .env.example                 # Environment template
├── alembic.ini                  # Alembic migration configuration
├── requirements.txt             # Production dependencies
└── requirements-dev.txt         # Development & test dependencies
```

---

## Security & Row-Level Security (RLS)

Every tenant-scoped table (`users`, `bots`, `documents`, `document_versions`, `chunks`, `queries`, `audit_log`) is protected with PostgreSQL Row Level Security (RLS):

```sql
ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;
ALTER TABLE <table> FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_<table> ON <table>
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
```

- **FORCE ROW LEVEL SECURITY** ensures that queries run through the application role are always filtered by tenant context.
- `tenant_session(tenant_id)` automatically issues `SET LOCAL app.tenant_id = ...` inside a dedicated transaction block, preventing any cross-tenant data leakage even with connection pooling.
- `tenants` and `platform_admins` are globally isolated tables without RLS, permitting authentication and tenant resolution.

---

## Prerequisites & Setup

- **Python 3.11+**
- **PostgreSQL 15+** with `pgvector` extension (e.g. Supabase or local Postgres)
- **Redis 7+** (Upstash or local Redis for background ingestion queues)
- **Google Gemini API Key** (for text embeddings)

### 1. Installation

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Environment Configuration

Copy the example environment template:

```bash
cp .env.example .env
```

Configure your `.env` variables:
- `DATABASE_URL`: Async PostgreSQL connection string (`postgresql+asyncpg://...`)
- `MIGRATE_URL`: Synchronous/Session pooler URL for Alembic migrations (`postgresql+psycopg2://...`)
- `JWT_SECRET`: 64-character random hex string (`python -c "import secrets; print(secrets.token_hex(32))"`)
- `REDIS_URL`: Redis / Upstash connection URL
- `GOOGLE_API_KEY`: Google AI Studio API key for Gemini embeddings
- `CORS_ORIGINS`: Allowed web clients (`http://localhost:3000,https://cortexa-io.vercel.app`)

### 3. Database Migrations

Apply the database schema and RLS policies:

```bash
alembic upgrade head
```

### 4. Running the Development Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`. Interactive documentation is accessible at `http://localhost:8000/docs`.

### 5. Running the Background Ingestion Worker

In a separate terminal:

```bash
python -m app.worker.ingestion
```

---

## API Endpoints Summary

| Method | Path | Description | Access |
|---|---|---|---|
| `GET` | `/health` | Service health status | Public |
| `POST` | `/auth/register` | Organization self-service signup | Public (Rate-limited) |
| `POST` | `/auth/login` | Tenant user authentication | Public |
| `POST` | `/auth/platform-login` | Platform administrator authentication | Platform Admin |
| `GET` | `/auth/me` | Current authenticated user profile | Authenticated |
| `POST` | `/auth/refresh` | Exchange refresh token for new access token | Authenticated |
| `POST` | `/api/v1/bots` | Create a new custom assistant bot | Tenant Admin |
| `GET` | `/api/v1/bots` | List all assistants for tenant | Tenant Admin |
| `GET` | `/api/v1/bots/{bot_id}` | Retrieve assistant details & widget configuration | Tenant Admin |
| `POST` | `/api/v1/bots/{bot_id}/documents/upload` | Upload PDF/text document for ingestion | Tenant Admin |
| `GET` | `/api/v1/bots/{bot_id}/documents` | List documents and ingestion status | Tenant Admin |
| `GET` | `/api/v1/bots/{bot_id}/documents/{doc_id}` | Detailed document status & versions | Tenant Admin |
| `DELETE`| `/api/v1/bots/{bot_id}/documents/{doc_id}` | Delete document and chunk vectors | Tenant Admin |

---

## Running Automated Tests

Run the complete test suite:

```bash
pytest
```

Run tenant isolation verification:

```bash
pytest tests/test_tenant_isolation.py -v
```
