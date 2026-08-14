import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    secret_key: str = os.getenv("SECRET_KEY", "development-only-change-me")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://consistency_user:change-me@localhost:3306/consistency_ai",
    )
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "development-only-change-me")
    cors_origins: list[str] = None  # type: ignore[assignment]
    ai_provider: str = os.getenv("AI_PROVIDER", "mock")

    def __post_init__(self):
        object.__setattr__(
            self,
            "cors_origins",
            [x.strip() for x in os.getenv(
                "CORS_ORIGINS", "http://localhost:5173"
            ).split(",") if x.strip()],
        )
