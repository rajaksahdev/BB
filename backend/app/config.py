"""Application configuration loaded from environment variables.

Uses pydantic-settings so config is validated at startup and secrets stay in
the environment (never in code). See backend/.env.example for the full list.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core
    app_env: str = "development"
    log_level: str = "info"

    # Comma-separated list of allowed browser origins (the deployed frontend).
    # Dev defaults cover Vite (5173) and CRA (3000).
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Database
    database_url: str = (
        "postgresql+psycopg://backtestlab:backtestlab@localhost:5432/backtestlab"
    )

    # Market data (Phase 1)
    binance_base_url: str = "https://api.binance.com"

    # Auth (Phase 3 — Supabase)
    supabase_jwt_secret: str = ""
    supabase_jwt_aud: str = "authenticated"
    # When true, accept "Bearer dev:<email>" tokens for local testing without
    # Supabase. MUST be false in production.
    auth_dev_mode: bool = True

    # Free-tier monthly saved-backtest limit (Pro = unlimited). FR-06.
    free_monthly_limit: int = 5

    # Billing (Phase 5 — Stripe). Empty == billing disabled; endpoints 503 and
    # the frontend hides upgrade UI. Fill these to turn billing on.
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro: str = ""  # the recurring Price ID for the Pro plan
    # Where Stripe Checkout / Portal send the user back to.
    frontend_url: str = "http://localhost:5173"

    @property
    def billing_enabled(self) -> bool:
        return bool(self.stripe_secret_key and self.stripe_price_pro)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sqlalchemy_url(self) -> str:
        """DB URL with an explicit driver.

        Managed Postgres providers (Render, Railway, Supabase, Heroku) hand back
        ``postgres://`` or ``postgresql://`` URLs; SQLAlchemy needs the psycopg
        driver spelled out. Normalize so the same env var works everywhere.
        """
        url = self.database_url
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://") :]
        return url


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
