from datetime import datetime, timezone
from flask import Blueprint, g, jsonify, request
from pydantic import ValidationError
from ...core.auth import require_auth
from ...core.database import db
from ...models.daily_task import DailyTask
from ...schemas.daily_task import DailyTaskCreate, DailyTaskResponse

daily_tasks_bp = Blueprint("daily_tasks", __name__)

@daily_tasks_bp.get("/daily-tasks")
@require_auth
def list_tasks():
    requested_date = request.args.get("date")
    query = DailyTask.query.filter_by(user_id=g.user_id)
    if requested_date:
        try:
            query = query.filter_by(scheduled_for=datetime.strptime(requested_date, "%Y-%m-%d").date())
        except ValueError:
            return jsonify({"error": "date must use YYYY-MM-DD"}), 400
    tasks = query.order_by(DailyTask.id.asc()).all()
    return jsonify([DailyTaskResponse.model_validate(t).model_dump(mode="json") for t in tasks])

@daily_tasks_bp.post("/daily-tasks")
@require_auth
def create_task():
    try:
        payload = DailyTaskCreate.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": "Invalid task", "details": exc.errors()}), 400
    task = DailyTask(user_id=g.user_id, **payload.model_dump())
    db.session.add(task)
    db.session.commit()
    return jsonify(DailyTaskResponse.model_validate(task).model_dump(mode="json")), 201

@daily_tasks_bp.patch("/daily-tasks/<int:task_id>/completion")
@require_auth
def set_completion(task_id: int):
    task = DailyTask.query.filter_by(id=task_id, user_id=g.user_id).first()
    if not task:
        return jsonify({"error": "Task not found"}), 404
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload.get("completed"), bool):
        return jsonify({"error": "completed must be boolean"}), 400
    task.completed = payload["completed"]
    task.completed_at = datetime.now(timezone.utc) if task.completed else None
    db.session.commit()
    return jsonify(DailyTaskResponse.model_validate(task).model_dump(mode="json"))
