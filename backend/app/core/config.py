"""
Central app configuration, loaded from environment variables.
Never hardcode secrets here — this file only defines *where* they come from.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Postgres — use the transaction pooler URL in production (e.g. Supabase port 6543)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/cortexa"
    # Migration URL — session pooler (port 5432) or direct connection for Alembic DDL
    MIGRATE_URL: str | None = None

    # Redis / job queue — Upstash or local
    REDIS_URL: str = "redis://localhost:6379"

    # JWT
    JWT_SECRET: str = "change-me-in-.env-never-commit-this"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS — comma-separated string from CORS_ORIGINS, or list in ALLOWED_ORIGINS
    CORS_ORIGINS: str | None = None
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "https://cortexa-io.vercel.app",
    ]

    def get_cors_origins(self) -> list[str]:
        if self.CORS_ORIGINS:
            origins = [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
            if origins:
                return origins
        return self.ALLOWED_ORIGINS

    # Embedding
    GOOGLE_API_KEY: str = ""
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_DIM: int = 768  # must match your chosen embedding model — lock before real ingestion

    # Embedding quota / throttle controls
    # EMBED_BATCH_SIZE: max texts per embed_content call
    EMBED_BATCH_SIZE: int = 16
    # EMBED_MAX_RPM: token-bucket capacity and refill rate (requests per minute) per API key
    EMBED_MAX_RPM: int = 60
    # EMBED_MAX_TPM: max tokens per minute per API key (conservative char/3 estimate)
    EMBED_MAX_TPM: int = 20_000
    # EMBED_MAX_WAIT_SECONDS: cap on total 429-throttle wait per job before giving up
    EMBED_MAX_WAIT_SECONDS: int = 900

    # Ingestion worker — Redis stream block time (milliseconds).
    # XREADGROUP blocks for this long when the stream is empty.
    # socket_timeout is set to (WORKER_BLOCK_MS / 1000) + 10 s so the
    # socket never times out during a legitimate blocked read.
    # Production default: 30 000 ms (30 s).
    # Set to 2 000 in .env.test for faster test teardown.
    WORKER_BLOCK_MS: int = 30_000

    # File storage (local; swapped for S3-compatible in production)
    STORAGE_DIR: str = "storage"

    # Optional: non-superuser role to SET LOCAL ROLE to inside every session.
    # Required when DATABASE_URL connects as a superuser (e.g. postgres) but
    # you want RLS policies to apply — superusers bypass RLS by default even
    # with FORCE ROW LEVEL SECURITY. In production, use a non-superuser role
    # in DATABASE_URL directly and leave this unset.
    APP_DB_ROLE: str | None = None

    # Document parsing & text gate
    MIN_EXTRACTED_CHARS: int = 20
    MIN_PRINTABLE_RATIO: float = 0.9
    MAX_PDF_PAGES: int = 500



settings = Settings()
