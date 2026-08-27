from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_health_and_dashboard_contract():
    assert client.get("/health").status_code == 200
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200
    assert [item["alert"]["id"] for item in response.json()["alerts"]] == ["A1", "A2", "A3", "A4", "A5"]


def test_missing_alert_is_not_found():
    assert client.get("/api/v1/alerts/unknown").status_code == 404
