"""The coach conversation: load it, add to it, or start a fresh one.

The reply streams as server-sent events. Two things make that slightly more
careful than an ordinary route:

* every database read the generator needs is done *before* streaming starts, so
  the response can begin without holding query state open across the stream, and
* the assistant turn is written when the stream finishes, from the text that was
  actually sent — never from what we intended to send.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator

from flask import Blueprint, Response, g, jsonify, stream_with_context

from ...core.auth import require_auth
from ...schemas.chat import ChatMessageResponse, ChatRequest
from ...services.ai_service import AIService
from ...services.chat_service import (
    ASSISTANT_ROLE,
    USER_ROLE,
    ChatService,
    coach_context,
)
from ..helpers import ApiError, enforce_ai_quota, serialize_many, validated

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat", __name__)

# Shown only if a reply produces no text at all — the user must never be left
# looking at an empty bubble.
EMPTY_REPLY = (
    "I lost my train of thought there. Ask me that again and I'll pick it back up."
)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@chat_bp.get("/coach/conversation")
@require_auth
def get_conversation():
    """The open thread, or an empty one. Never creates a row just by looking."""
    service = ChatService(g.user_id)
    conversation = service.active_conversation()
    if conversation is None:
        return jsonify(
            {"id": None, "messages": [], "ai_provider": AIService().provider_name}
        )
    return jsonify(
        {
            "id": conversation.id,
            "title": conversation.title,
            "messages": serialize_many(
                ChatMessageResponse, service.messages(conversation.id)
            ),
            "ai_provider": AIService().provider_name,
        }
    )


@chat_bp.post("/coach/conversation/reset")
@require_auth
def reset_conversation():
    """Close the thread. The messages stay in the database; a new one opens lazily."""
    ChatService(g.user_id).start_new()
    return jsonify({"id": None, "messages": []})


@chat_bp.post("/coach/chat")
@require_auth
def chat():
    payload = validated(ChatRequest)
    # Charged before the user turn is stored, so a refused request leaves no
    # half-exchange in the thread.
    enforce_ai_quota()
    user_id = g.user_id
    service = ChatService(user_id)

    conversation = service.active_conversation(create=True)
    conversation_id = conversation.id

    if service.is_full(conversation_id):
        raise ApiError(
            "This conversation has gotten long. Start a new one to keep going.", 409
        )

    user_message = service.append(conversation_id, USER_ROLE, payload.message)
    user_message_id = user_message.id

    # Everything the stream needs, resolved up front.
    history = service.history(conversation_id)
    context = coach_context(user_id)
    display_name = service.display_name()
    ai = AIService()

    def events() -> Iterator[str]:
        yield _sse(
            "start",
            {
                "conversation_id": conversation_id,
                "message_id": user_message_id,
                "ai_provider": ai.provider_name,
            },
        )

        parts: list[str] = []
        try:
            for piece in ai.chat_stream(history, context, display_name):
                parts.append(piece)
                yield _sse("delta", {"text": piece})
        except Exception:  # noqa: BLE001 — a stream must still close cleanly
            logger.exception("Coach chat stream failed for user %s", user_id)

        answer = "".join(parts).strip()
        if not answer:
            answer = EMPTY_REPLY
            yield _sse("delta", {"text": answer})

        stored = ChatService(user_id).append(conversation_id, ASSISTANT_ROLE, answer)
        yield _sse("done", {"message_id": stored.id})

    return Response(
        stream_with_context(events()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Tells nginx and friends not to buffer the reply into one lump,
            # which would defeat streaming on most production deployments.
            "X-Accel-Buffering": "no",
        },
    )
