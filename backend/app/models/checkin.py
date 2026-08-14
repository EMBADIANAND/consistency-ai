from datetime import datetime, timezone, date
from sqlalchemy import Text, Date
from ..core.database import db

class DailyCheckIn(db.Model):
    __tablename__ = "daily_check_ins"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    checkin_date = db.Column(Date, nullable=False, index=True)
    mood = db.Column(db.String(32), nullable=True)
    reflection = db.Column(Text, nullable=True)
    completed_tasks = db.Column(db.Integer, nullable=False, default=0)
    total_tasks = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        db.UniqueConstraint("user_id", "checkin_date", name="uq_checkin_user_date"),
    )
