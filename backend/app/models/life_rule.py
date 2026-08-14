from datetime import datetime, timezone
from sqlalchemy import String, Text
from ..core.database import db

class LifeRule(db.Model):
    __tablename__ = "life_rules"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(String(120), nullable=False)
    description = db.Column(Text, nullable=True)
    emoji = db.Column(String(16), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
