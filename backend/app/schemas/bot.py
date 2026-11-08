from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class BotCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., pattern=r"^[a-z0-9-]{1,63}$")
    branding_json: dict[str, Any] = Field(default_factory=dict)
    llm_overrides: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional per-bot API keys, e.g. {'groq_api_key': '...', "
            "'gemini_api_key': '...', 'embedding_api_key': '...'}. "
            "null means 'use platform defaults from settings'."
        ),
    )


class BotCreateResponse(BaseModel):
    bot_id: UUID
    slug: str
    name: str
    status: str
    widget_key: str  # raw key returned ONCE — only the hash is stored
    created_at: datetime


class BotUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    branding_json: dict[str, Any] | None = None


class BotDetail(BaseModel):
    bot_id: UUID
    tenant_id: UUID
    name: str
    slug: str
    branding_json: dict[str, Any]
    # llm_overrides deliberately omitted — never expose stored key material
    status: str
    document_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class BotListResponse(BaseModel):
    bots: list[BotDetail]
    total: int

