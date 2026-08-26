"""Stored coach conversations.

Storing the turns is what separates a conversation from a search box. The
previous coach endpoint answered each question in isolation, so a follow-up
like "why?" had nothing to refer back to. Persisting both sides of every
exchange means the model can be handed the thread, and the user can close the
tab without losing it.
"""

from datetime import datetime, timezone

from sqlalchemy import Text

from ..core.database import db

USER_ROLE = "user"
ASSISTANT_ROLE = "assistant"
ROLES = (USER_ROLE, ASSISTANT_ROLE)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(120), nullable=True)
    # Exactly one conversation per user is active. "Start fresh" deactivates the
    # current one instead of deleting it, so a past thread is never destroyed by
    # a single click — the same reasoning as the soft delete on life rules.
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    messages = db.relationship(
        "ChatMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.id",
        lazy="selectin",
    )


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(
        db.Integer,
        db.ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = db.Column(db.String(16), nullable=False)
    content = db.Column(Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)

    conversation = db.relationship("Conversation", back_populates="messages")
