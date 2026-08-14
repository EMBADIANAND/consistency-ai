from flask import Blueprint, jsonify, request
from pydantic import BaseModel, Field, ValidationError
from ...services.auth_service import AuthService

auth_bp = Blueprint("auth", __name__)
service = AuthService()

class AuthPayload(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, min_length=1, max_length=100)

@auth_bp.post("/auth/register")
def register():
    try:
        payload = AuthPayload.model_validate(request.get_json(silent=True) or {})
        if not payload.display_name:
            return jsonify({"error": "display_name is required"}), 400
        token = service.register(payload.email, payload.password, payload.display_name)
        return jsonify({"access_token": token}), 201
    except ValidationError as exc:
        return jsonify({"error": "Invalid registration data", "details": exc.errors()}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 409

@auth_bp.post("/auth/login")
def login():
    try:
        payload = AuthPayload.model_validate(request.get_json(silent=True) or {})
        token = service.login(payload.email, payload.password)
        return jsonify({"access_token": token})
    except ValidationError as exc:
        return jsonify({"error": "Invalid login data", "details": exc.errors()}), 400
    except ValueError:
        return jsonify({"error": "Invalid email or password"}), 401
