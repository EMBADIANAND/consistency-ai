"""The daily AI cap. Without it one account can spend the whole API budget."""

import pytest

from app import create_app
from app.core.database import db
from app.services.rate_limit import consume, usage_today


@pytest.fixture
def capped_app(settings):
    """An app whose allowance is small enough to exhaust in a test."""
    application = create_app(settings.__class__(**{**settings.__dict__, "ai_daily_limit": 3}))
    application.config.update(TESTING=True)
    with application.app_context():
        yield application
        db.session.remove()


@pytest.fixture
def capped_client(capped_app):
    return capped_app.test_client()


@pytest.fixture
def capped_auth(capped_client):
    def _register(email: str = "capped@example.com") -> dict:
        response = capped_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "strong-password", "display_name": "Capped"},
        )
        assert response.status_code == 201, response.get_json()
        return {"Authorization": f"Bearer {response.get_json()['access_token']}"}

    return _register


def test_the_cap_refuses_once_the_allowance_is_gone(capped_client, capped_auth):
    headers = capped_auth()
    for _ in range(3):
        assert (
            capped_client.post(
                "/api/v1/coach/ask", headers=headers, json={"question": "How am I doing?"}
            ).status_code
            == 200
        )

    refused = capped_client.post(
        "/api/v1/coach/ask", headers=headers, json={"question": "How am I doing?"}
    )
    assert refused.status_code == 429
    assert "limit" in refused.get_json()["error"].lower()


def test_a_refused_request_does_not_push_the_count_higher(capped_client, capped_auth, capped_app):
    headers = capped_auth()
    for _ in range(5):
        capped_client.post("/api/v1/coach/ask", headers=headers, json={"question": "Hi?"})

    from app.models.user import User

    user_id = User.query.filter_by(email="capped@example.com").one().id
    # Three consumed, two refused — retrying must not inflate the tally.
    assert usage_today(user_id) == 3


def test_the_cap_is_per_user(capped_client, capped_auth):
    first = capped_auth("one@example.com")
    second = capped_auth("two@example.com")
    for _ in range(3):
        capped_client.post("/api/v1/coach/ask", headers=first, json={"question": "Hi?"})

    assert (
        capped_client.post("/api/v1/coach/ask", headers=first, json={"question": "Hi?"}).status_code
        == 429
    )
    assert (
        capped_client.post(
            "/api/v1/coach/ask", headers=second, json={"question": "Hi?"}
        ).status_code
        == 200
    )


def test_a_refused_chat_leaves_no_half_exchange(capped_client, capped_auth):
    """A 429 must not store the user's turn — the thread would show a question
    that was never answered."""
    headers = capped_auth()
    for _ in range(3):
        capped_client.post("/api/v1/coach/chat", headers=headers, json={"message": "Hello"})

    before = capped_client.get("/api/v1/coach/conversation", headers=headers).get_json()
    refused = capped_client.post(
        "/api/v1/coach/chat", headers=headers, json={"message": "One more"}
    )
    after = capped_client.get("/api/v1/coach/conversation", headers=headers).get_json()

    assert refused.status_code == 429
    assert len(after["messages"]) == len(before["messages"])


def test_a_limit_of_zero_disables_the_cap(app):
    quota = consume(user_id=1, limit=0)
    assert quota.allowed is True


def test_the_default_app_has_a_cap_configured(app):
    assert app.config["APP_SETTINGS"].ai_daily_limit > 0
