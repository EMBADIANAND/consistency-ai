from datetime import date, datetime, timezone

from flask import Blueprint, g, jsonify, request

from ...core.auth import require_auth
from ...core.database import db
from ...models.daily_task import DailyTask
from ...models.life_rule import LifeRule
from ...schemas.daily_task import DailyPlanCreate, DailyTaskCreate, DailyTaskResponse
from ..helpers import ApiError, query_date, serialize, serialize_many, validated

daily_tasks_bp = Blueprint("daily_tasks", __name__)


def _owned_task(task_id: int) -> DailyTask:
    task = DailyTask.query.filter_by(id=task_id, user_id=g.user_id).first()
    if task is None:
        raise ApiError("Task not found", 404)
    return task


def _validate_rule(rule_id: int | None) -> None:
    """Never let a task point at somebody else's life rule."""
    if rule_id is None:
        return
    if not LifeRule.query.filter_by(id=rule_id, user_id=g.user_id).first():
        raise ApiError("Life rule not found", 404)


@daily_tasks_bp.get("/daily-tasks")
@require_auth
def list_tasks():
    query = DailyTask.query.filter_by(user_id=g.user_id)
    if request.args.get("date"):
        query = query.filter_by(scheduled_for=query_date())
    elif request.args.get("from") or request.args.get("to"):
        start = query_date("from", date.today())
        end = query_date("to", date.today())
        query = query.filter(DailyTask.scheduled_for.between(start, end))
    tasks = query.order_by(DailyTask.scheduled_for.asc(), DailyTask.id.asc()).all()
    return jsonify(serialize_many(DailyTaskResponse, tasks))


@daily_tasks_bp.post("/daily-tasks")
@require_auth
def create_task():
    payload = validated(DailyTaskCreate)
    _validate_rule(payload.life_rule_id)
    task = DailyTask(user_id=g.user_id, **payload.model_dump())
    db.session.add(task)
    db.session.commit()
    return jsonify(serialize(DailyTaskResponse, task)), 201


@daily_tasks_bp.put("/daily-tasks/plan")
@require_auth
def save_plan():
    """Replace one day's plan.

    Tasks the user removed are deleted; tasks that survive keep their id and
    completion state, so saving a plan never silently un-completes work.
    """
    payload = validated(DailyPlanCreate)
    for item in payload.tasks:
        _validate_rule(item.life_rule_id)

    existing = DailyTask.query.filter_by(
        user_id=g.user_id, scheduled_for=payload.scheduled_for
    ).all()
    by_key: dict[tuple[str, int | None], DailyTask] = {
        (task.title.strip().lower(), task.life_rule_id): task for task in existing
    }
    keep: set[int] = set()

    for item in payload.tasks:
        key = (item.title.strip().lower(), item.life_rule_id)
        task = by_key.get(key)
        if task is None:
            task = DailyTask(
                user_id=g.user_id,
                title=item.title.strip(),
                emoji=item.emoji,
                scheduled_for=payload.scheduled_for,
                life_rule_id=item.life_rule_id,
            )
            db.session.add(task)
            db.session.flush()
        else:
            task.emoji = item.emoji
        if item.completed != task.completed:
            task.completed = item.completed
            task.completed_at = datetime.now(timezone.utc) if item.completed else None
        keep.add(task.id)

    for task in existing:
        if task.id not in keep:
            db.session.delete(task)

    db.session.commit()
    tasks = (
        DailyTask.query.filter_by(user_id=g.user_id, scheduled_for=payload.scheduled_for)
        .order_by(DailyTask.id.asc())
        .all()
    )
    return jsonify(serialize_many(DailyTaskResponse, tasks))


@daily_tasks_bp.patch("/daily-tasks/<int:task_id>/completion")
@require_auth
def set_completion(task_id: int):
    task = _owned_task(task_id)
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload.get("completed"), bool):
        raise ApiError("completed must be true or false")
    task.completed = payload["completed"]
    task.completed_at = datetime.now(timezone.utc) if task.completed else None
    db.session.commit()
    return jsonify(serialize(DailyTaskResponse, task))


@daily_tasks_bp.delete("/daily-tasks/<int:task_id>")
@require_auth
def delete_task(task_id: int):
    task = _owned_task(task_id)
    db.session.delete(task)
    db.session.commit()
    return "", 204
