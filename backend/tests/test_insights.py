from datetime import date, timedelta

TODAY = date.today()


def _plan(client, headers, day, titles, completed_titles=()):
    response = client.put(
        "/api/v1/daily-tasks/plan",
        headers=headers,
        json={
            "scheduled_for": day.isoformat(),
            "tasks": [
                {"title": title, "completed": title in completed_titles} for title in titles
            ],
        },
    )
    assert response.status_code == 200
    return response.get_json()


def test_today_summary_reflects_real_tasks(client, auth):
    headers = auth()
    _plan(client, headers, TODAY, ["A", "B", "C", "D"], completed_titles={"A", "B", "C"})

    summary = client.get("/api/v1/summary/today", headers=headers).get_json()
    assert summary["total_tasks"] == 4
    assert summary["completed_tasks"] == 3
    assert summary["completion_rate"] == 75
    assert summary["streak"] == 1
    assert summary["display_name"] == "Test User"
    assert summary["headline"] == "Steady progress."


def test_empty_account_reports_zeroes_not_errors(client, auth):
    headers = auth()
    summary = client.get("/api/v1/summary/today", headers=headers).get_json()
    assert summary["total_tasks"] == 0
    assert summary["completion_rate"] == 0
    assert summary["streak"] == 0

    journey = client.get("/api/v1/journey", headers=headers).get_json()
    assert journey["score"] == 0
    assert journey["traits"] == ["🌤️ Just beginning"]

    report = client.get("/api/v1/reports/weekly", headers=headers).get_json()
    assert report["consistency"] == 0
    assert report["patterns"]


def test_streak_survives_an_unplanned_today_but_breaks_on_a_missed_day(client, auth):
    headers = auth()
    for offset in (1, 2, 3):
        day = TODAY - timedelta(days=offset)
        _plan(client, headers, day, ["Move"], completed_titles={"Move"})

    # Nothing planned today yet — yesterday's run should still stand.
    assert client.get("/api/v1/summary/today", headers=headers).get_json()["streak"] == 3

    # A planned-but-missed day two days ago would have cut the run short.
    _plan(client, headers, TODAY - timedelta(days=2), ["Move"])
    assert client.get("/api/v1/summary/today", headers=headers).get_json()["streak"] == 1


def test_weekly_report_covers_the_whole_week_but_scores_only_elapsed_days(client, auth):
    headers = auth()
    _plan(client, headers, TODAY, ["A", "B"], completed_titles={"A"})
    report = client.get("/api/v1/reports/weekly", headers=headers).get_json()

    # A Monday-to-Sunday chart, so the shape doesn't change as the week fills in.
    assert len(report["days"]) == 7
    assert [day["label"] for day in report["days"]][0] == "Mon"

    elapsed = [day for day in report["days"] if not day["future"]]
    assert len(elapsed) == TODAY.weekday() + 1
    assert elapsed[-1]["date"] == TODAY.isoformat()
    # Days still to come must not drag the percentage down.
    assert report["consistency"] == 50
    assert report["ai_provider"] == "mock"


def test_future_days_are_not_eligible_to_be_the_best_day(client, auth):
    headers = auth()
    _plan(client, headers, TODAY, ["A", "B"], completed_titles={"A"})
    report = client.get("/api/v1/reports/weekly", headers=headers).get_json()
    labels = {day["label"] for day in report["days"] if not day["future"]}
    assert report["best_day"] in labels


def test_coach_answers_are_grounded_in_the_users_numbers(client, auth):
    headers = auth()
    _plan(client, headers, TODAY, ["A", "B"], completed_titles={"A", "B"})

    response = client.post(
        "/api/v1/coach/ask", headers=headers, json={"question": "How long is my streak?"}
    )
    assert response.status_code == 200
    body = response.get_json()
    assert "1" in body["answer"]
    assert body["ai_provider"] == "mock"

    prompt = client.get("/api/v1/coach/prompt", headers=headers).get_json()
    assert prompt["title"] and prompt["body"]


def test_coach_rejects_an_empty_question(client, auth):
    headers = auth()
    assert (
        client.post("/api/v1/coach/ask", headers=headers, json={"question": ""}).status_code
        == 400
    )


def test_check_in_returns_an_insight_and_can_be_read_back(client, auth):
    headers = auth()
    _plan(client, headers, TODAY, ["A", "B"], completed_titles={"A"})

    response = client.post(
        "/api/v1/check-ins",
        headers=headers,
        json={"checkin_date": TODAY.isoformat(), "mood": "🙂", "reflection": "Mixed day."},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["check_in"]["completed_tasks"] == 1
    assert body["check_in"]["total_tasks"] == 2
    assert body["insight"]["title"] and body["insight"]["body"]

    stored = client.get(f"/api/v1/check-ins/{TODAY.isoformat()}", headers=headers).get_json()
    assert stored["mood"] == "🙂"
    assert client.get("/api/v1/check-ins", headers=headers).get_json()[0]["mood"] == "🙂"


def test_check_in_is_idempotent_for_a_day(client, auth):
    headers = auth()
    for mood in ("😐", "😄"):
        client.post(
            "/api/v1/check-ins",
            headers=headers,
            json={"checkin_date": TODAY.isoformat(), "mood": mood},
        )
    stored = client.get("/api/v1/check-ins", headers=headers).get_json()
    assert len(stored) == 1
    assert stored[0]["mood"] == "😄"


def test_missing_check_in_reads_as_null(client, auth):
    headers = auth()
    response = client.get(f"/api/v1/check-ins/{TODAY.isoformat()}", headers=headers)
    assert response.status_code == 200
    assert response.get_json() is None
