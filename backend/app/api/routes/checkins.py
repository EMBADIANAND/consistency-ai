from flask import Blueprint, g, jsonify

from ...core.auth import require_auth
from ...core.database import db
from ...models.checkin import DailyCheckIn
from ...models.daily_task import DailyTask
from ...schemas.checkin import CheckInCreate, CheckInResponse
from ...services.ai_service import AIService
from ...services.date_utils import parse_date
from ..helpers import ApiError, serialize, serialize_many, validated

checkins_bp = Blueprint("checkins", __name__)


@checkins_bp.get("/check-ins")
@require_auth
def list_checkins():
    checkins = (
        DailyCheckIn.query.filter_by(user_id=g.user_id)
        .order_by(DailyCheckIn.checkin_date.desc())
        .limit(30)
        .all()
    )
    return jsonify(serialize_many(CheckInResponse, checkins))


@checkins_bp.get("/check-ins/<string:day>")
@require_auth
def get_checkin(day: str):
    try:
        parsed = parse_date(day)
    except ValueError as exc:
        raise ApiError("date must use YYYY-MM-DD") from exc
    checkin = DailyCheckIn.query.filter_by(user_id=g.user_id, checkin_date=parsed).first()
    if checkin is None:
        return jsonify(None)
    return jsonify(serialize(CheckInResponse, checkin))


@checkins_bp.post("/check-ins")
@require_auth
def create_or_update_checkin():
    """Record the end-of-day reflection and return the AI response to it."""
    payload = validated(CheckInCreate)

    tasks = DailyTask.query.filter_by(
        user_id=g.user_id, scheduled_for=payload.checkin_date
    ).all()
    checkin = DailyCheckIn.query.filter_by(
        user_id=g.user_id, checkin_date=payload.checkin_date
    ).first()
    if checkin is None:
        checkin = DailyCheckIn(user_id=g.user_id, checkin_date=payload.checkin_date)
        db.session.add(checkin)

    checkin.mood = payload.mood
    checkin.reflection = payload.reflection
    checkin.total_tasks = len(tasks)
    checkin.completed_tasks = sum(1 for task in tasks if task.completed)
    db.session.commit()

    insight = AIService().daily_reflection(
        checkin.completed_tasks, checkin.total_tasks, checkin.mood
    )
    return jsonify(
        {"check_in": serialize(CheckInResponse, checkin), "insight": insight.to_dict()}
    ), 200
