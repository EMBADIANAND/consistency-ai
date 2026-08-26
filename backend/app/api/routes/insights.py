"""Derived views of a user's history: today, weekly reports, journey, coach."""

from datetime import date, datetime

from flask import Blueprint, g, jsonify
from pydantic import BaseModel, Field

from ...core.auth import require_auth
from ...core.database import db
from ...models.user import User
from ...services.ai_service import AIService
from ...services.chat_service import coach_context
from ...services.stats_service import StatsService
from ..helpers import enforce_ai_quota, query_date, validated

insights_bp = Blueprint("insights", __name__)


class CoachQuestion(BaseModel):
    question: str = Field(min_length=2, max_length=800)


def _greeting(hour: int) -> str:
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


@insights_bp.get("/summary/today")
@require_auth
def today_summary():
    day = query_date(fallback=date.today())
    stats = StatsService(g.user_id)
    summary = stats.today_summary(day)
    user = db.session.get(User, g.user_id)
    summary["greeting"] = _greeting(datetime.now().hour)
    summary["display_name"] = user.display_name if user else "there"
    return jsonify(summary)


@insights_bp.get("/reports/weekly")
@require_auth
def weekly_report():
    day = query_date(fallback=date.today())
    report = StatsService(g.user_id).weekly_report(day)
    service = AIService()
    report["patterns"] = [i.to_dict() for i in service.weekly_patterns(report)]
    report["ai_provider"] = service.provider_name
    return jsonify(report)


@insights_bp.get("/journey")
@require_auth
def journey():
    day = query_date(fallback=date.today())
    return jsonify(StatsService(g.user_id).journey(day))


@insights_bp.post("/coach/ask")
@require_auth
def coach_ask():
    """One-shot question with no memory.

    Superseded by ``POST /coach/chat``, which remembers the thread. Left in
    place because it is a stable endpoint and now shares the same grounding
    numbers, so the two can never disagree about the user's week.
    """
    payload = validated(CoachQuestion)
    enforce_ai_quota()
    context = coach_context(g.user_id)
    service = AIService()
    return jsonify(
        {
            "question": payload.question,
            "answer": service.coach_answer(payload.question, context),
            "ai_provider": service.provider_name,
        }
    )


@insights_bp.get("/coach/prompt")
@require_auth
def coach_prompt():
    """The 'I noticed something' card the Coach screen opens with."""
    stats = StatsService(g.user_id)
    journey_stats = stats.journey()
    planned_rules = [
        rule
        for rule in stats.rule_breakdown(date.today().replace(day=1), date.today())
        if rule["planned"] > 0
    ]
    strongest = max(planned_rules, key=lambda r: r["rate"], default=None)

    if journey_stats["tasks_planned"] == 0:
        body = "You haven't planned anything yet. One intention tomorrow is enough to start."
    elif strongest and strongest["rate"] >= 60:
        body = (
            f"{strongest['emoji'] or '✅'} {strongest['title']} is the promise you keep most "
            f"reliably — {strongest['rate']}% this month."
        )
    else:
        body = (
            f"You're keeping {journey_stats['reliability']}% of what you plan. Planning fewer "
            "things usually raises that number, not more discipline."
        )
    return jsonify({"title": "✨ I noticed something", "body": body})
