"""A per-user, per-day tally of AI-answered requests.

Kept in the database rather than in process memory on purpose: gunicorn runs
several workers, and an in-memory counter would let a user spend N times the
limit simply by being load-balanced across them. One row per user per day is
cheap, and it survives a restart.
"""

from datetime import date, datetime, timezone

from ..core.database import db


class AiUsage(db.Model):
    __tablename__ = "ai_usage"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    usage_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    count = db.Column(db.Integer, nullable=False, default=0)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        db.UniqueConstraint("user_id", "usage_date", name="uq_ai_usage_user_date"),
    )
