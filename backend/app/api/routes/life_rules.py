from datetime import date, datetime, timezone

from flask import Blueprint, g, jsonify

from ...core.auth import require_auth
from ...core.database import db
from ...models.daily_task import DailyTask
from ...models.life_rule import LifeRule
from ...schemas.life_rule import LifeRuleCreate, LifeRuleUpdate
from ...services.stats_service import StatsService
from ..helpers import ApiError, query_date, validated

life_rules_bp = Blueprint("life_rules", __name__)


def _rule_payload(rule: LifeRule, stats: StatsService, day: date) -> dict:
    """A rule plus the two facts the Rules screen needs: streak and today's state."""
    done_today = (
        DailyTask.query.filter_by(
            user_id=rule.user_id,
            life_rule_id=rule.id,
            scheduled_for=day,
            completed=True,
        ).first()
        is not None
    )
    return {
        "id": rule.id,
        "title": rule.title,
        "description": rule.description,
        "emoji": rule.emoji,
        "is_active": rule.is_active,
        "streak": stats.rule_streak(rule.id, day),
        "done_today": done_today,
    }


def _owned_rule(rule_id: int) -> LifeRule:
    rule = LifeRule.query.filter_by(id=rule_id, user_id=g.user_id).first()
    if rule is None:
        raise ApiError("Life rule not found", 404)
    return rule


@life_rules_bp.get("/life-rules")
@require_auth
def list_rules():
    day = query_date(fallback=date.today())
    rules = (
        LifeRule.query.filter_by(user_id=g.user_id, is_active=True)
        .order_by(LifeRule.created_at.asc())
        .all()
    )
    stats = StatsService(g.user_id)
    return jsonify([_rule_payload(rule, stats, day) for rule in rules])


@life_rules_bp.post("/life-rules")
@require_auth
def create_rule():
    payload = validated(LifeRuleCreate)
    rule = LifeRule(user_id=g.user_id, **payload.model_dump())
    db.session.add(rule)
    db.session.commit()
    return jsonify(_rule_payload(rule, StatsService(g.user_id), date.today())), 201


@life_rules_bp.patch("/life-rules/<int:rule_id>")
@require_auth
def update_rule(rule_id: int):
    rule = _owned_rule(rule_id)
    payload = validated(LifeRuleUpdate)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value.strip() if isinstance(value, str) else value)
    db.session.commit()
    return jsonify(_rule_payload(rule, StatsService(g.user_id), date.today()))


@life_rules_bp.delete("/life-rules/<int:rule_id>")
@require_auth
def delete_rule(rule_id: int):
    rule = _owned_rule(rule_id)
    # Soft delete: the rule disappears from the app but its history stays intact,
    # so past reports do not silently change.
    rule.is_active = False
    db.session.commit()
    return "", 204


@life_rules_bp.post("/life-rules/<int:rule_id>/complete")
@require_auth
def complete_rule(rule_id: int):
    """Mark a rule kept for a day.

    Keeping a rule is recorded as a completed daily task linked to it, so rules
    and planned intentions share one history and one definition of a streak.
    """
    rule = _owned_rule(rule_id)
    day = query_date(fallback=date.today())
    task = DailyTask.query.filter_by(
        user_id=g.user_id, life_rule_id=rule.id, scheduled_for=day
    ).first()
    if task is None:
        task = DailyTask(
            user_id=g.user_id,
            life_rule_id=rule.id,
            title=rule.title,
            emoji=rule.emoji,
            scheduled_for=day,
        )
        db.session.add(task)

    task.completed = not task.completed
    task.completed_at = datetime.now(timezone.utc) if task.completed else None
    db.session.commit()
    return jsonify(_rule_payload(rule, StatsService(g.user_id), day))
