from flask import Blueprint, g, jsonify, request
from pydantic import ValidationError
from ...core.auth import require_auth
from ...core.database import db
from ...models.checkin import DailyCheckIn
from ...models.daily_task import DailyTask
from ...schemas.checkin import CheckInCreate, CheckInResponse

checkins_bp = Blueprint("checkins", __name__)

@checkins_bp.post("/check-ins")
@require_auth
def create_or_update_checkin():
    try:
        payload = CheckInCreate.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": "Invalid check-in", "details": exc.errors()}), 400

    tasks = DailyTask.query.filter_by(user_id=g.user_id, scheduled_for=payload.checkin_date).all()
    checkin = DailyCheckIn.query.filter_by(user_id=g.user_id, checkin_date=payload.checkin_date).first()
    if checkin is None:
        checkin = DailyCheckIn(user_id=g.user_id, checkin_date=payload.checkin_date)
        db.session.add(checkin)

    checkin.mood = payload.mood
    checkin.reflection = payload.reflection
    checkin.total_tasks = len(tasks)
    checkin.completed_tasks = sum(task.completed for task in tasks)
    db.session.commit()

    return jsonify(CheckInResponse.model_validate(checkin).model_dump(mode="json")), 200
