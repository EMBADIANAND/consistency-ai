from functools import wraps
from flask import g, jsonify, request
import jwt
from .config import Settings

def issue_access_token(user_id: int, settings: Settings) -> str:
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(hours=1)}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")

def require_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "Authentication required"}), 401
        token = header.removeprefix("Bearer ").strip()
        try:
            payload = jwt.decode(token, Settings().jwt_secret_key, algorithms=["HS256"])
            g.user_id = int(payload["sub"])
        except (jwt.InvalidTokenError, KeyError, ValueError):
            return jsonify({"error": "Invalid or expired authentication token"}), 401
        return view(*args, **kwargs)
    return wrapped
