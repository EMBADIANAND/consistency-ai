from datetime import datetime, timezone
from sqlalchemy import String, Date
from ..core.database import db

class DailyTask(db.Model):
    __tablename__ = "daily_tasks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    life_rule_id = db.Column(db.Integer, db.ForeignKey("life_rules.id", ondelete="SET NULL"), nullable=True, index=True)
    title = db.Column(String(180), nullable=False)
    emoji = db.Column(String(16), nullable=True)
    scheduled_for = db.Column(Date, nullable=False, index=True)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
