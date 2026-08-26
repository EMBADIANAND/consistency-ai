"""A daily cap on AI-answered requests.

Without this, one authenticated account can loop a request and spend the whole
API budget. The cap is per user per day, counted in the database so it holds
across every gunicorn worker.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.exc import IntegrityError

from ..core.database import db
from ..models.ai_usage import AiUsage


@dataclass(frozen=True)
class Quota:
    allowed: bool
    used: int
    limit: int

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)


def _row_for_today(user_id: int, day: date) -> AiUsage:
    row = AiUsage.query.filter_by(user_id=user_id, usage_date=day).first()
    if row is not None:
        return row
    row = AiUsage(user_id=user_id, usage_date=day, count=0)
    db.session.add(row)
    try:
        db.session.flush()
    except IntegrityError:
        # Two concurrent first-requests of the day raced; the other one won.
        db.session.rollback()
        row = AiUsage.query.filter_by(user_id=user_id, usage_date=day).one()
    return row


def consume(user_id: int, limit: int, day: date | None = None) -> Quota:
    """Count one AI request against today's allowance.

    Returns ``allowed=False`` without incrementing once the cap is reached, so a
    user who keeps retrying cannot push the number higher. A limit of 0 or less
    disables the cap entirely.
    """
    if limit <= 0:
        return Quota(allowed=True, used=0, limit=limit)

    day = day or date.today()
    row = _row_for_today(user_id, day)

    if row.count >= limit:
        db.session.commit()
        return Quota(allowed=False, used=row.count, limit=limit)

    row.count += 1
    db.session.commit()
    return Quota(allowed=True, used=row.count, limit=limit)


def usage_today(user_id: int, day: date | None = None) -> int:
    row = AiUsage.query.filter_by(
        user_id=user_id, usage_date=day or date.today()
    ).first()
    return row.count if row else 0
