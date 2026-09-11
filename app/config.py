"""Strongly typed application configuration.

Settings are grouped by category (application, database, redis, LLM providers,
model routing, browser, social integrations, security, logging, limits) per
PROJECT.md section 38. All configuration is sourced from environment
variables / a local .env file and never hard-coded.
"""

from __future__ import annotations

from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# LiteLLM (and vendor SDKs it wraps) read provider API keys directly from
# the process environment, not through pydantic-settings -- so .env must be
# materialized into os.environ, not just parsed into the Settings model.
load_dotenv()


class ApplicationSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_")

    name: str = "agent-operator"
    environment: str = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DATABASE_")

    url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/agent_operator"
    )
    pool_size: int = 5
    max_overflow: int = 10
    echo: bool = False


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REDIS_")

    url: str = "redis://localhost:6379/0"
    max_connections: int = 10


class LLMProviderSettings(BaseSettings):
    """Credentials/config for LangChain-compatible model providers.

    No single provider is required at import time; each is optional so the
    application can start without every key configured. Providers are only
    exercised when a route actually needs them. Model routing goes through
    LiteLLM (see app.llm.providers.litellm_provider), which reads these same
    variable names directly from the environment -- setting them here keeps
    them documented and validated in one place.
    """

    model_config = SettingsConfigDict(env_prefix="")

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    openrouter_api_key: str | None = None

    #: Point at a self-hosted LiteLLM proxy ("omnirouter") instead of
    #: calling vendor APIs directly -- centralizes keys, budgets, and
    #: cross-provider fallback routing behind one gateway.
    litellm_api_base: str | None = None
    litellm_api_key: str | None = None


class ModelRoutingSettings(BaseSettings):
    """Model names are LiteLLM model strings, e.g. ``"gpt-4o-mini"``,
    ``"claude-3-5-sonnet-20241022"``, ``"gemini/gemini-1.5-pro"``, or
    ``"openrouter/anthropic/claude-3.5-sonnet"`` -- any backend LiteLLM
    supports, picked per model class independent of any other class."""

    model_config = SettingsConfigDict(env_prefix="MODEL_ROUTER_")

    fast_model: str = "gpt-4o-mini"
    tool_calling_model: str = "gpt-4o"
    reasoning_model: str = "gpt-4o"
    strongest_model: str = "gpt-4o"
    default_provider: str = "litellm"


class BrowserSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BROWSER_")

    headless: bool = True
    default_timeout_ms: int = 30_000
    navigation_timeout_ms: int = 30_000
    user_data_dir: str | None = None


class SocialSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="")

    x_client_id: str | None = None
    x_client_secret: str | None = None
    linkedin_client_id: str | None = None
    linkedin_client_secret: str | None = None


class SecuritySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SECURITY_")

    secret_key: str = "insecure-development-key-change-me"
    allowed_hosts: list[str] = Field(default_factory=lambda: ["*"])
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])


class LoggingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LOG_")

    level: str = "INFO"
    json_format: bool = True


class LimitSettings(BaseSettings):
    """Bounds preventing unbounded agent loops and runaway cost (PROJECT.md 9, 40)."""

    model_config = SettingsConfigDict(env_prefix="LIMITS_")

    max_iterations: int = 25
    max_tool_calls: int = 50
    max_execution_seconds: int = 900
    max_retries: int = 3
    max_research_sources: int = 15


class Settings(BaseSettings):
    """Top-level settings aggregating every configuration category."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    application: ApplicationSettings = Field(default_factory=ApplicationSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    llm: LLMProviderSettings = Field(default_factory=LLMProviderSettings)
    model_routing: ModelRoutingSettings = Field(default_factory=ModelRoutingSettings)
    browser: BrowserSettings = Field(default_factory=BrowserSettings)
    social: SocialSettings = Field(default_factory=SocialSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    limits: LimitSettings = Field(default_factory=LimitSettings)


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton.

    Cached so configuration is parsed once; tests can call
    ``get_settings.cache_clear()`` to reload after mutating the environment.
    """

    return Settings()
