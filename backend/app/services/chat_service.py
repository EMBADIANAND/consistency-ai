"""Reading and writing the coach conversation.

The route layer never touches the conversation tables directly; it asks this
service, which owns two decisions that matter:

* how much of the thread is replayed to the model (``HISTORY_TURNS``), which is
  the difference between a coach that remembers and an unbounded bill, and
* how long a single thread may grow before the user is nudged to start a new
  one (``MAX_MESSAGES``).
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from ..core.database import db
from ..models.conversation import ASSISTANT_ROLE, USER_ROLE, ChatMessage, Conversation
from ..models.user import User
from .stats_service import StatsService

# Turns handed to the model. Twelve is roughly six exchanges — enough that a
# thread holds its thread of thought, small enough that a long conversation
# cannot quietly grow the cost of every reply.
HISTORY_TURNS = 12

# A single conversation is capped so the table cannot grow without bound from
# one very long session; the UI offers "start fresh" well before this.
MAX_MESSAGES = 400

TITLE_LENGTH = 60


def coach_context(user_id: int, today: date | None = None) -> dict:
    """The numbers the coach is allowed to cite.

    Built here rather than in a route so the one-shot ``/coach/ask`` endpoint
    and the streaming conversation always ground their answers in exactly the
    same figures.
    """
    day = today or date.today()
    stats = StatsService(user_id)
    report = stats.weekly_report(day)
    journey = stats.journey(day)
    return {
        "consistency": report["consistency"],
        "previous_consistency": report["previous_consistency"],
        "delta": report["delta"],
        "best_day": report["best_day"],
        "current_streak": journey["current_streak"],
        "longest_streak": journey["longest_streak"],
        "score": journey["score"],
        "rule_breakdown": report["rule_breakdown"],
    }


class ChatService:
    def __init__(self, user_id: int):
        self.user_id = user_id

    # ----------------------------------------------------------------- reads

    def active_conversation(self, create: bool = False) -> Conversation | None:
        conversation = (
            Conversation.query.filter_by(user_id=self.user_id, is_active=True)
            .order_by(Conversation.id.desc())
            .first()
        )
        if conversation is None and create:
            conversation = Conversation(user_id=self.user_id, is_active=True)
            db.session.add(conversation)
            db.session.commit()
        return conversation

    def messages(self, conversation_id: int) -> list[ChatMessage]:
        return (
            ChatMessage.query.filter_by(conversation_id=conversation_id)
            .order_by(ChatMessage.id)
            .all()
        )

    def history(self, conversation_id: int) -> list[dict]:
        """The recent thread, oldest first, in the shape a provider expects.

        The window is trimmed to start on a user turn: a history that opens with
        an assistant message reads to the model as if it spoke unprompted.
        """
        recent = self.messages(conversation_id)[-HISTORY_TURNS:]
        while recent and recent[0].role != USER_ROLE:
            recent.pop(0)
        return [{"role": m.role, "content": m.content} for m in recent]

    def display_name(self) -> str:
        user = db.session.get(User, self.user_id)
        return user.display_name if user else "there"

    # ---------------------------------------------------------------- writes

    def append(self, conversation_id: int, role: str, content: str) -> ChatMessage:
        message = ChatMessage(
            conversation_id=conversation_id, role=role, content=content
        )
        db.session.add(message)

        conversation = db.session.get(Conversation, conversation_id)
        if conversation is not None:
            conversation.updated_at = datetime.now(timezone.utc)
            # The first thing the user said names the thread, which is all the
            # title is for — there is no model call just to label a chat.
            if not conversation.title and role == USER_ROLE:
                conversation.title = content.strip()[:TITLE_LENGTH]

        db.session.commit()
        return message

    def start_new(self) -> None:
        """Close the current thread. Nothing is deleted; a new one opens lazily."""
        Conversation.query.filter_by(user_id=self.user_id, is_active=True).update(
            {"is_active": False}
        )
        db.session.commit()

    def is_full(self, conversation_id: int) -> bool:
        count = ChatMessage.query.filter_by(conversation_id=conversation_id).count()
        return count >= MAX_MESSAGES


__all__ = ["ChatService", "coach_context", "USER_ROLE", "ASSISTANT_ROLE"]
