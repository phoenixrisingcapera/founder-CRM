from pydantic import BaseModel


class ApiKeySaveRequest(BaseModel):
    provider: str
    api_key: str


class ApiKeySummaryResponse(BaseModel):
    provider: str
    configured: bool


class SettingsSummaryResponse(BaseModel):
    exports_enabled: bool
    api_keys: list[ApiKeySummaryResponse]


class SignedArtifactUrlResponse(BaseModel):
    artifact_id: str
    download_url: str
