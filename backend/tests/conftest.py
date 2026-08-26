import pytest

from app import create_app
from app.core.config import Settings
from app.core.database import db


@pytest.fixture
def settings() -> Settings:
    return Settings(
        env="testing",
        secret_key="test-secret",
        jwt_secret_key="test-jwt-secret",
        database_url="sqlite:///:memory:",
        cors_origins=["http://localhost:5173"],
        ai_provider="mock",
        frontend_dist="/tmp/does-not-exist",
        auto_create_tables=True,
    )


@pytest.fixture
def app(settings):
    application = create_app(settings)
    application.config.update(TESTING=True)
    with application.app_context():
        yield application
        db.session.remove()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth(client):
    """Register a user and return a helper that signs requests as them."""

    def _register(email: str = "test@example.com", name: str = "Test User") -> dict:
        response = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "strong-password", "display_name": name},
        )
        assert response.status_code == 201, response.get_json()
        token = response.get_json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _register
