def test_health_reports_database(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["service"] == "consistency-ai"


def test_unknown_api_route_returns_json(client):
    response = client.get("/api/v1/nope")
    assert response.status_code == 404
    assert "error" in response.get_json()
