"""The conversation: does it remember, does it persist, does it degrade well."""

import json

import pytest

from app.core.config import Settings
from app.core.database import db
from app.models.conversation import ChatMessage, Conversation
from app.services.ai_service import AnthropicProvider, RuleBasedProvider
from app.services.chat_service import HISTORY_TURNS, ChatService

CHAT_URL = "/api/v1/coach/chat"
CONVERSATION_URL = "/api/v1/coach/conversation"


def parse_sse(raw: str) -> list[tuple[str, dict]]:
    """Turn a raw event-stream body into (event, data) pairs."""
    events = []
    for block in raw.strip().split("\n\n"):
        if not block.strip():
            continue
        name, payload = None, None
        for line in block.splitlines():
            if line.startswith("event:"):
                name = line[len("event:") :].strip()
            elif line.startswith("data:"):
                payload = json.loads(line[len("data:") :].strip())
        if name:
            events.append((name, payload or {}))
    return events


def say(client, headers, message: str) -> str:
    """Send one turn and return the assistant's full reply text."""
    response = client.post(CHAT_URL, json={"message": message}, headers=headers)
    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.mimetype == "text/event-stream"
    events = parse_sse(response.get_data(as_text=True))
    assert events[0][0] == "start"
    assert events[-1][0] == "done"
    return "".join(data["text"] for name, data in events if name == "delta")


# --------------------------------------------------------------- persistence


def test_conversation_starts_empty_without_creating_a_row(client, auth):
    headers = auth()
    response = client.get(CONVERSATION_URL, headers=headers)
    assert response.status_code == 200
    assert response.get_json() == {
        "id": None,
        "messages": [],
        "ai_provider": "mock",
    }
    # Merely opening the screen must not litter the table.
    assert Conversation.query.count() == 0


def test_both_sides_of_an_exchange_are_stored(client, auth):
    headers = auth()
    reply = say(client, headers, "What should I focus on tomorrow?")
    assert reply.strip()

    stored = ChatMessage.query.order_by(ChatMessage.id).all()
    assert [m.role for m in stored] == ["user", "assistant"]
    assert stored[0].content == "What should I focus on tomorrow?"
    assert stored[1].content == reply.strip()


def test_history_survives_a_reload(client, auth):
    headers = auth()
    say(client, headers, "How long is my streak?")
    say(client, headers, "And what about consistency?")

    messages = client.get(CONVERSATION_URL, headers=headers).get_json()["messages"]
    assert [m["role"] for m in messages] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert messages[0]["content"] == "How long is my streak?"


def test_the_thread_is_titled_by_its_first_message(client, auth):
    headers = auth()
    say(client, headers, "Where am I losing consistency?")
    assert Conversation.query.first().title == "Where am I losing consistency?"


def test_reset_closes_the_thread_but_keeps_what_was_said(client, auth):
    headers = auth()
    say(client, headers, "How long is my streak?")
    assert ChatMessage.query.count() == 2

    response = client.post(f"{CONVERSATION_URL}/reset", headers=headers)
    assert response.status_code == 200
    assert client.get(CONVERSATION_URL, headers=headers).get_json()["messages"] == []

    # Nothing was destroyed — the old thread was only deactivated.
    assert ChatMessage.query.count() == 2
    assert Conversation.query.filter_by(is_active=False).count() == 1

    say(client, headers, "Starting again")
    assert Conversation.query.filter_by(is_active=True).count() == 1


def test_one_users_conversation_is_invisible_to_another(client, auth):
    mine = auth("me@example.com", "Me")
    say(client, mine, "How long is my streak?")

    theirs = auth("them@example.com", "Them")
    assert client.get(CONVERSATION_URL, headers=theirs).get_json()["messages"] == []


def test_chat_requires_authentication(client):
    assert client.post(CHAT_URL, json={"message": "hello"}).status_code == 401
    assert client.get(CONVERSATION_URL).status_code == 401


@pytest.mark.parametrize("message", ["", "   ", "x" * 2001])
def test_unusable_messages_are_rejected(client, auth, message):
    headers = auth()
    response = client.post(CHAT_URL, json={"message": message}, headers=headers)
    assert response.status_code == 400
    assert ChatMessage.query.count() == 0


# ------------------------------------------------------------------- memory


def test_a_short_follow_up_is_answered_in_light_of_the_last_question(client, auth):
    """'Why?' on its own is the whole point of having a conversation."""
    headers = auth()
    first = say(client, headers, "Where am I losing consistency?")
    second = say(client, headers, "why?")

    # It must not be treated as a brand new, topicless question...
    assert second.strip()
    # ...and it must not simply repeat the sentence already on screen.
    assert second.strip() != first.strip()


def test_a_greeting_is_answered_as_a_greeting(client, auth):
    """'hey' should be met by a hello, not by a consistency briefing."""
    reply = say(client, auth(email="hi@example.com", name="Anand"), "hey")
    assert reply.startswith("Hey Anand")
    assert reply.rstrip().endswith("?")  # it hands the turn back
    assert "keeping" not in reply  # not the generic stats fallback


def test_gratitude_does_not_trigger_another_lecture(client, auth):
    reply = say(client, auth(), "thanks")
    assert "Anytime" in reply


def test_a_one_day_streak_is_counted_in_the_singular(app):
    provider = RuleBasedProvider()
    context = {"consistency": 50, "current_streak": 1, "longest_streak": 4, "rule_breakdown": []}

    greeting = provider.chat([{"role": "user", "content": "hey"}], context, "Anand")
    assert "1 day into a streak" in greeting
    assert "1 days" not in greeting

    answer = provider.coach_answer("How long is my streak?", context)
    assert "1 day," in answer
    assert "1 days" not in answer


def test_the_model_only_sees_a_window_that_starts_on_a_user_turn(client, auth):
    """A history opening mid-answer reads as the assistant speaking unprompted."""
    headers = auth()
    for index in range(HISTORY_TURNS):
        say(client, headers, f"question number {index}")

    conversation = Conversation.query.first()
    service = ChatService(conversation.user_id)

    # Long past the window, so it must have been trimmed.
    assert ChatMessage.query.count() == HISTORY_TURNS * 2
    history = service.history(conversation.id)
    assert len(history) <= HISTORY_TURNS
    assert history[0]["role"] == "user"

    # And as the route sees it — the newest user turn is appended before the
    # history is read, so the window always ends on the question being answered.
    service.append(conversation.id, "user", "the newest question")
    mid_request = service.history(conversation.id)
    assert mid_request[0]["role"] == "user"
    assert mid_request[-1]["content"] == "the newest question"


def test_repeating_yourself_gets_a_different_angle(app):
    provider = RuleBasedProvider()
    context = {
        "consistency": 60,
        "current_streak": 3,
        "longest_streak": 9,
        "rule_breakdown": [
            {"id": 1, "title": "Evening walk", "emoji": "🚶", "planned": 5, "kept": 1, "rate": 20}
        ],
    }
    question = "Where am I losing consistency?"
    first = provider.chat([{"role": "user", "content": question}], context)
    second = provider.chat(
        [
            {"role": "user", "content": question},
            {"role": "assistant", "content": first},
            {"role": "user", "content": question},
        ],
        context,
    )
    assert second != first
    assert "evening walk" in second.lower()


# ------------------------------------------------------- provider behaviour


class _Stub(AnthropicProvider):
    """An Anthropic provider whose upstream stream we control."""

    def __init__(self, chunks, fail_after=None):
        super().__init__(
            Settings(ai_provider="anthropic", ai_api_key="k"), RuleBasedProvider()
        )
        self.chunks = chunks
        self.fail_after = fail_after

    def _stream_chat(self, history, system):
        for index, chunk in enumerate(self.chunks):
            if self.fail_after is not None and index == self.fail_after:
                raise TimeoutError("upstream died")
            yield chunk


def test_a_failure_before_the_first_token_falls_back_to_the_rule_based_answer():
    provider = _Stub(chunks=["never sent"], fail_after=0)
    history = [{"role": "user", "content": "Where am I losing consistency?"}]
    context = {"consistency": 50, "current_streak": 2, "rule_breakdown": []}

    answer = "".join(provider.chat_stream(history, context, "Anand"))
    assert answer == provider.fallback.chat(history, context, "Anand")


def test_a_failure_mid_stream_keeps_what_the_user_already_read():
    """Swapping in a different answer here would contradict the screen."""
    provider = _Stub(chunks=["You're ", "holding ", "steady"], fail_after=2)
    context = {"consistency": 50, "current_streak": 2, "rule_breakdown": []}

    answer = "".join(
        provider.chat_stream([{"role": "user", "content": "how am I?"}], context)
    )
    assert answer == "You're holding "
    assert "consistency" not in answer  # no rule-based text was appended


def test_stats_are_restated_in_the_system_block_on_every_call():
    """Numbers in the transcript would age out of the window as it grows."""
    provider = _Stub(chunks=["ok"])
    system = provider._chat_system({"consistency": 73}, "Anand")
    assert '"consistency": 73' in system
    assert "Anand" in system
    assert "only numbers you may cite" in system


def test_an_empty_reply_never_leaves_an_empty_bubble(client, auth, monkeypatch):
    monkeypatch.setattr(RuleBasedProvider, "chat_stream", lambda *a, **k: iter(()))
    headers = auth()
    reply = say(client, headers, "anything")
    assert "lost my train of thought" in reply
    assert ChatMessage.query.filter_by(role="assistant").first().content == reply


def test_a_follow_up_after_only_a_greeting_goes_deeper_not_generic(client, auth):
    """"hey" then "why?" must not be answered as if "hey" were the question."""
    headers = auth()
    say(client, headers, "hey")
    say(client, headers, "why?")

    messages = client.get("/api/v1/coach/conversation", headers=headers).get_json()[
        "messages"
    ]
    replies = [m["content"] for m in messages if m["role"] == "assistant"]
    assert len(replies) == 2
    assert replies[1] != replies[0]
    assert replies[1].startswith("Going one level deeper:")
