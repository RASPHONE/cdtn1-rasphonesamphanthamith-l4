def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}


def test_health_reports_database_down(client, monkeypatch):
    monkeypatch.setattr("src.routes.health.ping", lambda: False)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "down"}
