from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AiStack Founder CRM API"
    app_env: str = Field(default="development", alias="CRM_APP_ENV")
    database_url: str = Field(default="sqlite:///./aistack_founder_crm.db", alias="CRM_DATABASE_URL")
    auth_secret_key: str = Field(default="change-me", alias="CRM_AUTH_SECRET_KEY")
    encryption_key: str = Field(default="", alias="CRM_ENCRYPTION_KEY")
    cors_origins: str = Field(default="http://localhost:5174", alias="CRM_CORS_ORIGINS")
    exports_enabled: bool = Field(default=False, alias="CRM_EXPORTS_ENABLED")
    openai_api_key: str = Field(default="", alias="CRM_OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="CRM_OPENAI_MODEL")
    openrouter_api_key: str = Field(default="", alias="CRM_OPENROUTER_API_KEY")
    openrouter_model: str = Field(default="openai/gpt-4o-mini", alias="CRM_OPENROUTER_MODEL")
    uploads_root: str = Field(default="./storage/uploads", alias="CRM_UPLOADS_ROOT")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def uploads_root_path(self) -> Path:
        return Path(self.uploads_root).resolve()


settings = Settings()
