from flask import Blueprint, g, jsonify

from ...core.auth import require_auth
from ...core.database import db
from ...models.user import User
from ...schemas.user import LoginPayload, RegisterPayload, UserResponse
from ...services.auth_service import AuthService
from ..helpers import ApiError, serialize, validated

auth_bp = Blueprint("auth", __name__)
service = AuthService()


@auth_bp.post("/auth/register")
def register():
    payload = validated(RegisterPayload)
    try:
        user, token = service.register(payload.email, payload.password, payload.display_name)
    except ValueError as exc:
        raise ApiError(str(exc), 409) from exc
    return jsonify({"access_token": token, "user": serialize(UserResponse, user)}), 201


@auth_bp.post("/auth/login")
def login():
    payload = validated(LoginPayload)
    try:
        user, token = service.login(payload.email, payload.password)
    except ValueError as exc:
        raise ApiError("Invalid email or password", 401) from exc
    return jsonify({"access_token": token, "user": serialize(UserResponse, user)})


@auth_bp.get("/auth/me")
@require_auth
def me():
    user = db.session.get(User, g.user_id)
    if user is None:
        raise ApiError("Account no longer exists", 401)
    return jsonify(serialize(UserResponse, user))
