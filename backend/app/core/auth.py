"""JWT issuing and the authentication guard used by protected routes."""

from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request

from .config import Settings


def _settings() -> Settings:
    """Prefer the settings attached to the running app so tests can override them."""
    configured = current_app.config.get("APP_SETTINGS") if current_app else None
    return configured or Settings()


def issue_access_token(user_id: int, settings: Settings | None = None) -> str:
    settings = settings or _settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expires_hours),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def decode_access_token(token: str, settings: Settings | None = None) -> int:
    settings = settings or _settings()
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
    return int(payload["sub"])


def require_auth(view):
    """Reject the request unless it carries a valid bearer token.

    On success ``g.user_id`` holds the authenticated user's id, which every
    query in the application scopes by. There is no code path that reads a user
    id from the request body.
    """

    @wraps(view)
    def wrapped(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "Authentication required"}), 401
        token = header.removeprefix("Bearer ").strip()
        try:
            g.user_id = decode_access_token(token)
        except (jwt.InvalidTokenError, KeyError, ValueError):
            return jsonify({"error": "Invalid or expired authentication token"}), 401
        return view(*args, **kwargs)

    return wrapped
