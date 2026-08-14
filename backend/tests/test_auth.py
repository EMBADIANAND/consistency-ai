import pytest
from app import create_app
from app.core.database import db

@pytest.fixture
def app():
    app = create_app()
    app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

def test_register_and_login(app):
    client = app.test_client()
    response = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "strong-password",
        "display_name": "Test User",
    })
    assert response.status_code == 201
    token = response.get_json()["access_token"]
    assert token

    response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "strong-password",
    })
    assert response.status_code == 200
    assert response.get_json()["access_token"]
