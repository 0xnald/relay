from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="RELAY_",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Relay"
    environment: Literal["development", "test", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database_url: str = "postgresql+asyncpg://relay:relay@localhost:5432/relay"
    cors_origins: list[str] = Field(default_factory=list)
    agent_model_provider: Literal["bedrock"] = "bedrock"
    agent_model_id: str = Field(
        default="global.anthropic.claude-sonnet-4-6", min_length=1, max_length=255
    )
    aws_region: str = Field(default="us-east-1", min_length=1, max_length=64)
    agent_execution_mode: Literal["local", "agentcore"] = "local"
    agentcore_runtime_arn: str | None = None
    agentcore_region: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
