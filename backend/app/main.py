from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, tenants
from app.api.v1 import bots, documents
from app.core.config import settings

app = FastAPI(
    title="Cortexa Backend API",
    description="Multi-tenant knowledge base, document ingestion, embeddings, and bot management API engine for Cortexa.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication and tenant management routes (available at /auth and /api/auth)
app.include_router(auth.router)
app.include_router(tenants.router)
app.include_router(auth.router, prefix="/api")
app.include_router(tenants.router, prefix="/api")

# v1 versioned API routes
app.include_router(bots.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "cortexa-backend", "version": "1.0.0"}
