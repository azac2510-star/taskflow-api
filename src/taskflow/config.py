from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TaskFlow API"
    environment: str = "development"
    secret_key: str = "dev-only-change-this-secret-at-least-32-bytes-long"
    access_token_expire_minutes: int = 60
    database_url: str = "sqlite:///./taskflow.db"
    cors_origins: str = "http://localhost:3000,http://localhost:8000"
    auto_create_tables: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
