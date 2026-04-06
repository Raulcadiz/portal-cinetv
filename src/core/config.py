"""
Application settings loaded from environment variables / .env file.
Uses pydantic-settings (BaseSettings) for validation and type coercion.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration for IPTVSur Portal.

    Values are loaded in this order (highest priority first):
    1. Environment variables
    2. .env file (if present)
    3. Default values defined here
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./data/iptvsur.db"

    # ── Security ──────────────────────────────────────────────────────────────
    secret_key: str = "CHANGE_ME_IN_PRODUCTION_USE_OPENSSL_RAND_HEX_32"
    admin_username: str = "admin"
    admin_password: str = "CHANGE_ME_IN_PRODUCTION"

    # ── JWT ───────────────────────────────────────────────────────────────────
    jwt_ttl_hours: int = 24
    jwt_algorithm: str = "HS256"

    # ── Upload limits ─────────────────────────────────────────────────────────
    max_m3u8_size_mb: int = 50
    max_xmltv_size_mb: int = 100

    # ── CORS ──────────────────────────────────────────────────────────────────
    # TODO: Restrict to your domain in production (e.g. "https://your-portal.com")
    cors_origins: list[str] = ["*"]

    @property
    def max_m3u8_size_bytes(self) -> int:
        return self.max_m3u8_size_mb * 1024 * 1024

    @property
    def max_xmltv_size_bytes(self) -> int:
        return self.max_xmltv_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    Use this as a FastAPI dependency: ``settings: Settings = Depends(get_settings)``.
    """
    return Settings()


# Module-level singleton for convenience imports
settings = get_settings()
