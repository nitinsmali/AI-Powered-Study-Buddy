from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "mysql+aiomysql://study_user:study_pass@db:3306/study_buddy"

    # ── Clerk Auth ────────────────────────────────────────────────────────────
    CLERK_SECRET_KEY: str = ""
    CLERK_PUBLISHABLE_KEY: str = ""

    # ── LLM / AI ──────────────────────────────────────────────────────────────
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_BASE_URL: Optional[str] = None  # Leave None to use the OpenAI default

    # ── Storage ───────────────────────────────────────────────────────────────
    STORAGE_PATH: str = "./uploads"

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Stored as a plain string so pydantic_settings never tries JSON-parsing.
    # Use the `cors_origins_list` property wherever a list is needed.
    CORS_ORIGINS_STR: str = (
        "http://localhost:3000,http://localhost:5500,"
        "http://127.0.0.1:5500,http://localhost:8080,null"
    )

    @field_validator("LLM_BASE_URL", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        """Convert empty string to None so OpenAI client uses its default."""
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        """Return CORS origins as a list, parsed from the comma-separated string."""
        raw = self.CORS_ORIGINS_STR.strip()
        if not raw:
            return [
                "http://localhost:3000",
                "http://localhost:5500",
                "http://127.0.0.1:5500",
            ]
        # JSON array fallback
        if raw.startswith("["):
            import json
            try:
                return json.loads(raw)
            except Exception:
                pass
        return [o.strip() for o in raw.split(",") if o.strip()]

    # Keep CORS_ORIGINS as an alias so existing code using settings.CORS_ORIGINS still works
    @property
    def CORS_ORIGINS(self) -> List[str]:  # noqa: N802
        return self.cors_origins_list

    # ── Limits ────────────────────────────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = 50
    RATE_LIMIT_PER_MINUTE: int = 60

    # ── Application ───────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # ── Derived helpers ───────────────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def clerk_jwks_url(self) -> str:
        """Build the Clerk JWKS endpoint from the secret key prefix (sk_live_/sk_test_)."""
        # The frontend API key encodes the instance FAPI domain; the backend
        # can also derive it from the publishable key, but the safest approach
        # is the well-known URL for the Clerk instance.
        # Format: https://<instance>.clerk.accounts.dev/.well-known/jwks.json
        # We rely on the CLERK_PUBLISHABLE_KEY which starts with pk_test_ or pk_live_
        # followed by the base64-encoded frontend API URL.
        import base64

        pk = self.CLERK_PUBLISHABLE_KEY
        if not pk:
            return ""
        try:
            payload = pk.split("_", 2)[2]  # strip "pk_test_" or "pk_live_"
            # Add padding
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += "=" * padding
            fapi_url = base64.b64decode(payload).decode("utf-8").rstrip("$")
            return f"{fapi_url}/.well-known/jwks.json"
        except Exception:
            return ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
