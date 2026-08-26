from flask import Blueprint, g, jsonify

from ...core.auth import require_auth
from ...schemas.goal import GoalCreate, GoalResponse, GoalUpdate
from ...services.goal_service import GoalService
from ..helpers import ApiError, serialize, serialize_many, validated

goals_bp = Blueprint("goals", __name__)
service = GoalService()


@goals_bp.get("/goals")
@require_auth
def list_goals():
    return jsonify(serialize_many(GoalResponse, service.list_goals(g.user_id)))


@goals_bp.post("/goals")
@require_auth
def create_goal():
    goal = service.create_goal(g.user_id, validated(GoalCreate))
    return jsonify(serialize(GoalResponse, goal)), 201


@goals_bp.patch("/goals/<int:goal_id>")
@require_auth
def update_goal(goal_id: int):
    goal = service.update_goal(g.user_id, goal_id, validated(GoalUpdate))
    if goal is None:
        raise ApiError("Goal not found", 404)
    return jsonify(serialize(GoalResponse, goal))


@goals_bp.delete("/goals/<int:goal_id>")
@require_auth
def delete_goal(goal_id: int):
    if not service.delete_goal(g.user_id, goal_id):
        raise ApiError("Goal not found", 404)
    return "", 204
