from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

WorkspaceAiProvider = Literal["openai", "openrouter", "claude"]


class SaveWorkspaceAiProviderRequest(BaseModel):
    provider: WorkspaceAiProvider
    apiKey: str = Field(default="", min_length=0)
    preferredModel: str | None = None
    skipForNow: bool = False


class WorkspaceAiProviderSummary(BaseModel):
    provider: WorkspaceAiProvider | None
    preferred_model: str | None
    api_key_last4: str | None
    key_version: str | None = None
    is_configured: bool
    configured_at: datetime | None
    skipped_at: datetime | None


class SaveWorkspaceAiProviderResponse(BaseModel):
    summary: WorkspaceAiProviderSummary
    next_url: str


class RevokeWorkspaceAiProviderResponse(BaseModel):
    summary: WorkspaceAiProviderSummary
    revoked: bool
