from datetime import date

TODAY = date.today().isoformat()


def test_create_list_and_complete_a_task(client, auth):
    headers = auth()
    created = client.post(
        "/api/v1/daily-tasks",
        headers=headers,
        json={"title": "Gym before 7 AM", "emoji": "🏋️", "scheduled_for": TODAY},
    )
    assert created.status_code == 201
    task = created.get_json()
    assert task["completed"] is False

    listed = client.get(f"/api/v1/daily-tasks?date={TODAY}", headers=headers)
    assert [t["title"] for t in listed.get_json()] == ["Gym before 7 AM"]

    toggled = client.patch(
        f"/api/v1/daily-tasks/{task['id']}/completion",
        headers=headers,
        json={"completed": True},
    )
    assert toggled.status_code == 200
    assert toggled.get_json()["completed"] is True
    assert toggled.get_json()["completed_at"] is not None


def test_saving_a_plan_replaces_the_day_but_keeps_completions(client, auth):
    headers = auth()
    first = client.put(
        "/api/v1/daily-tasks/plan",
        headers=headers,
        json={
            "scheduled_for": TODAY,
            "tasks": [{"title": "Read 10 pages"}, {"title": "Walk 10k steps"}],
        },
    )
    assert first.status_code == 200
    tasks = {t["title"]: t for t in first.get_json()}
    assert len(tasks) == 2

    client.patch(
        f"/api/v1/daily-tasks/{tasks['Read 10 pages']['id']}/completion",
        headers=headers,
        json={"completed": True},
    )

    second = client.put(
        "/api/v1/daily-tasks/plan",
        headers=headers,
        json={
            "scheduled_for": TODAY,
            "tasks": [{"title": "Read 10 pages", "completed": True}, {"title": "Deep work"}],
        },
    )
    after = {t["title"]: t for t in second.get_json()}
    assert set(after) == {"Read 10 pages", "Deep work"}
    # The surviving task keeps its identity and its completion.
    assert after["Read 10 pages"]["id"] == tasks["Read 10 pages"]["id"]
    assert after["Read 10 pages"]["completed"] is True


def test_a_user_cannot_touch_another_users_task(client, auth):
    owner = auth("owner@example.com", "Owner")
    intruder = auth("intruder@example.com", "Intruder")
    task_id = client.post(
        "/api/v1/daily-tasks",
        headers=owner,
        json={"title": "Private task", "scheduled_for": TODAY},
    ).get_json()["id"]

    assert client.get("/api/v1/daily-tasks", headers=intruder).get_json() == []
    assert (
        client.patch(
            f"/api/v1/daily-tasks/{task_id}/completion",
            headers=intruder,
            json={"completed": True},
        ).status_code
        == 404
    )
    assert client.delete(f"/api/v1/daily-tasks/{task_id}", headers=intruder).status_code == 404


def test_task_cannot_reference_another_users_life_rule(client, auth):
    owner = auth("owner@example.com", "Owner")
    intruder = auth("intruder@example.com", "Intruder")
    rule_id = client.post(
        "/api/v1/life-rules", headers=owner, json={"title": "Move daily"}
    ).get_json()["id"]

    response = client.post(
        "/api/v1/daily-tasks",
        headers=intruder,
        json={"title": "Sneaky", "scheduled_for": TODAY, "life_rule_id": rule_id},
    )
    assert response.status_code == 404


def test_bad_date_is_rejected(client, auth):
    headers = auth()
    assert client.get("/api/v1/daily-tasks?date=23-08-2026", headers=headers).status_code == 400


def test_delete_removes_the_task(client, auth):
    headers = auth()
    task_id = client.post(
        "/api/v1/daily-tasks",
        headers=headers,
        json={"title": "Temporary", "scheduled_for": TODAY},
    ).get_json()["id"]
    assert client.delete(f"/api/v1/daily-tasks/{task_id}", headers=headers).status_code == 204
    assert client.get("/api/v1/daily-tasks", headers=headers).get_json() == []
