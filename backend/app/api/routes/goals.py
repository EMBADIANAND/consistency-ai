from flask import Blueprint, jsonify, request
from pydantic import ValidationError
from ...schemas.goal import GoalCreate, GoalResponse
from ...services.goal_service import GoalService

goals_bp = Blueprint("goals", __name__)
service = GoalService()

# Authentication is deliberately represented by a boundary for now.
# Production auth middleware will supply the authenticated user ID.
def current_user_id() -> int:
    user_id = request.headers.get("X-Demo-User-ID")
    if not user_id or not user_id.isdigit():
        raise PermissionError("Authenticated user required")
    return int(user_id)

@goals_bp.get("/goals")
def list_goals():
    try:
        goals = service.list_goals(current_user_id())
        return jsonify([GoalResponse.model_validate(g).model_dump() for g in goals])
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 401

@goals_bp.post("/goals")
def create_goal():
    try:
        payload = GoalCreate.model_validate(request.get_json(silent=True) or {})
        goal = service.create_goal(current_user_id(), payload)
        return jsonify(GoalResponse.model_validate(goal).model_dump()), 201
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 401
    except ValidationError as exc:
        return jsonify({"error": "Invalid goal", "details": exc.errors()}), 400
