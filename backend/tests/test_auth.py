def test_register_returns_token_and_user(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "Test@Example.com",
            "password": "strong-password",
            "display_name": "Test User",
        },
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["access_token"]
    assert body["user"]["email"] == "test@example.com"


def test_login_succeeds_and_me_returns_the_account(client, auth):
    headers = auth()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "strong-password"},
    )
    assert response.status_code == 200

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.get_json()["display_name"] == "Test User"


def test_duplicate_email_is_rejected(client, auth):
    auth()
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "another-password",
            "display_name": "Someone Else",
        },
    )
    assert response.status_code == 409


def test_bad_password_is_rejected(client, auth):
    auth()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_invalid_email_is_rejected(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "strong-password", "display_name": "X"},
    )
    assert response.status_code == 400
    assert response.get_json()["details"][0]["field"] == "email"


def test_short_password_is_rejected(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "a@b.com", "password": "short", "display_name": "X"},
    )
    assert response.status_code == 400


def test_protected_route_requires_a_token(client):
    assert client.get("/api/v1/daily-tasks").status_code == 401
    assert client.get("/api/v1/goals").status_code == 401
    assert (
        client.get("/api/v1/daily-tasks", headers={"Authorization": "Bearer nonsense"}).status_code
        == 401
    )
