from datetime import date, timedelta

TODAY = date.today()


def test_rule_lifecycle(client, auth):
    headers = auth()
    created = client.post(
        "/api/v1/life-rules",
        headers=headers,
        json={"title": "Move my body", "description": "Gym or walk", "emoji": "🏋️"},
    )
    assert created.status_code == 201
    rule = created.get_json()
    assert rule["streak"] == 0
    assert rule["done_today"] is False

    renamed = client.patch(
        f"/api/v1/life-rules/{rule['id']}", headers=headers, json={"title": "Move daily"}
    )
    assert renamed.get_json()["title"] == "Move daily"

    assert client.delete(f"/api/v1/life-rules/{rule['id']}", headers=headers).status_code == 204
    assert client.get("/api/v1/life-rules", headers=headers).get_json() == []


def test_completing_a_rule_builds_a_streak(client, auth):
    headers = auth()
    rule_id = client.post(
        "/api/v1/life-rules", headers=headers, json={"title": "Move my body", "emoji": "🏋️"}
    ).get_json()["id"]

    for offset in (2, 1, 0):
        day = (TODAY - timedelta(days=offset)).isoformat()
        response = client.post(
            f"/api/v1/life-rules/{rule_id}/complete?date={day}", headers=headers
        )
        assert response.status_code == 200

    listed = client.get("/api/v1/life-rules", headers=headers).get_json()[0]
    assert listed["streak"] == 3
    assert listed["done_today"] is True


def test_completing_twice_toggles_back_off(client, auth):
    headers = auth()
    rule_id = client.post(
        "/api/v1/life-rules", headers=headers, json={"title": "Read"}
    ).get_json()["id"]

    client.post(f"/api/v1/life-rules/{rule_id}/complete", headers=headers)
    second = client.post(f"/api/v1/life-rules/{rule_id}/complete", headers=headers)
    assert second.get_json()["done_today"] is False
    assert second.get_json()["streak"] == 0


def test_rules_are_scoped_to_their_owner(client, auth):
    owner = auth("owner@example.com", "Owner")
    intruder = auth("intruder@example.com", "Intruder")
    rule_id = client.post(
        "/api/v1/life-rules", headers=owner, json={"title": "Private rule"}
    ).get_json()["id"]

    assert client.get("/api/v1/life-rules", headers=intruder).get_json() == []
    assert (
        client.patch(
            f"/api/v1/life-rules/{rule_id}", headers=intruder, json={"title": "Hijacked"}
        ).status_code
        == 404
    )
