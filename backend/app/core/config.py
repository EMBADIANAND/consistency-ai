"""Application settings, loaded once from the environment."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load the .env that sits at the repository root (backend/app/core -> repo root)
_REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_REPO_ROOT / ".env")
load_dotenv()  # also honour a .env in the current working directory


def _split_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _normalize_database_url(raw: str) -> str:
    """Accept the URL shapes hosting providers hand out.

    Heroku-style platforms (Render included) expose ``postgres://…``, a scheme
    SQLAlchemy 2.x no longer recognises. Rewriting it here means the deployment
    works with whatever the provider injects, unedited.
    """
    if raw.startswith("postgres://"):
        return "postgresql+psycopg2://" + raw[len("postgres://") :]
    if raw.startswith("postgresql://"):
        return "postgresql+psycopg2://" + raw[len("postgresql://") :]
    if raw.startswith("mysql://"):
        return "mysql+pymysql://" + raw[len("mysql://") :]
    return raw


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of configuration.

    Every value can be overridden through the environment, which is what makes
    the same image runnable in development and in production.
    """

    env: str = field(default_factory=lambda: os.getenv("FLASK_ENV", "development"))
    secret_key: str = field(
        default_factory=lambda: os.getenv("SECRET_KEY", "development-only-change-me")
    )
    database_url: str = field(
        default_factory=lambda: _normalize_database_url(
            os.getenv("DATABASE_URL", "sqlite:///consistency_ai.db")
        )
    )
    jwt_secret_key: str = field(
        default_factory=lambda: os.getenv("JWT_SECRET_KEY", "development-only-change-me")
    )
    jwt_expires_hours: int = field(
        default_factory=lambda: int(os.getenv("JWT_EXPIRES_HOURS", "168"))
    )
    cors_origins: list[str] = field(
        default_factory=lambda: _split_csv(
            os.getenv("CORS_ORIGINS", "http://localhost:5173")
        )
    )
    ai_provider: str = field(default_factory=lambda: os.getenv("AI_PROVIDER", "mock"))
    ai_api_key: str | None = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY") or None
    )
    ai_model: str = field(
        default_factory=lambda: os.getenv("AI_MODEL", "claude-sonnet-4-5")
    )
    # AI-answered requests one account may make per day. Without a cap, a single
    # authenticated user can loop a request and spend the whole API budget.
    # Set to 0 to disable the cap.
    ai_daily_limit: int = field(
        default_factory=lambda: int(os.getenv("AI_DAILY_LIMIT", "100"))
    )
    # Directory holding the built frontend. When present, Flask serves the SPA
    # itself, so a single process covers the whole application in production.
    frontend_dist: str = field(
        default_factory=lambda: os.getenv(
            "FRONTEND_DIST", str(_REPO_ROOT / "frontend" / "dist")
        )
    )
    auto_create_tables: bool = field(
        default_factory=lambda: os.getenv("AUTO_CREATE_TABLES", "true").lower()
        in {"1", "true", "yes"}
    )

    @property
    def is_production(self) -> bool:
        return self.env.lower() in {"production", "prod"}

    def validate(self) -> list[str]:
        """Return a list of problems that would be unsafe in production."""
        problems: list[str] = []
        if not self.is_production:
            return problems
        if "change-me" in self.secret_key or self.secret_key == "development-only-change-me":
            problems.append("SECRET_KEY must be set to a real secret in production")
        if (
            "change-me" in self.jwt_secret_key
            or self.jwt_secret_key == "development-only-change-me"
        ):
            problems.append("JWT_SECRET_KEY must be set to a real secret in production")
        return problems
