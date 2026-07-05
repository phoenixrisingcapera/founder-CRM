from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr


class ConnectedAccountConnectRequest(BaseModel):
    provider: Literal["microsoft", "linkedin"]
    origin: str | None = None


class ConnectedAccountSummary(BaseModel):
    id: str
    userId: str
    provider: str
    status: str
    externalAccountId: str | None = None
    externalEmail: EmailStr | None = None
    externalDisplayName: str | None = None
    scopes: list[str] = []
    accessTokenMasked: str | None = None
    refreshTokenStored: bool = False
    externalProfileUrl: str | None = None
    lastSyncedAt: datetime | None = None
    syncMetadata: dict = {}
    createdAt: datetime | None = None
    updatedAt: datetime | None = None


class ConnectedAccountListRouteResponse(BaseModel):
    accounts: list[ConnectedAccountSummary]
