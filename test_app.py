from app import app, get_redis_client


def test_health():
    client = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_visits_uses_redis():
    redis_client = get_redis_client()
    redis_client.delete("visits")

    client = app.test_client()

    first_response = client.get("/visits")
    second_response = client.get("/visits")

    assert first_response.status_code == 200
    assert first_response.get_json()["visits"] == 1

    assert second_response.status_code == 200
    assert second_response.get_json()["visits"] == 2


def test_metrics():
    client = app.test_client()

    client.get("/health")
    response = client.get("/metrics")

    assert response.status_code == 200

    metrics = response.get_data(as_text=True)

    assert "http_requests_total" in metrics
    assert "http_request_duration_seconds" in metrics
    assert "app_deployed_version" in metrics
