from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

from ...core.database import db

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    """Liveness plus a real database round trip, so orchestrators see the truth."""
    settings = current_app.config.get("APP_SETTINGS")
    try:
        db.session.execute(text("SELECT 1"))
        database = "ok"
        status_code = 200
    except Exception:  # pragma: no cover - only on a genuinely broken database
        current_app.logger.exception("Health check could not reach the database")
        database = "unreachable"
        status_code = 503

    return (
        jsonify(
            {
                "status": "ok" if status_code == 200 else "degraded",
                "service": "consistency-ai",
                "database": database,
                "environment": settings.env if settings else "unknown",
                "ai_provider": settings.ai_provider if settings else "unknown",
            }
        ),
        status_code,
    )
