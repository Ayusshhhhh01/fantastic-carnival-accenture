from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_health_and_dashboard_contract():
    assert client.get("/health").status_code == 200
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200
    assert "alerts" in response.json()


def test_missing_alert_is_not_found():
    assert client.get("/api/v1/alerts/unknown").status_code == 404


def test_approve_removes_alert_from_active_dashboard():
    # 1. Load initial dashboard
    res1 = client.get("/api/v1/dashboard")
    assert res1.status_code == 200
    initial_alerts = [a["alert"]["id"] for a in res1.json()["alerts"]]
    
    # Target an alert that is present
    target_id = initial_alerts[0] if initial_alerts else "A1"
    
    # 2. Approve alert
    post_res = client.post(f"/api/v1/alerts/{target_id}/decisions", json={
        "decision": "approved",
        "persona": "Category Manager",
        "feedback": "Approved in regression test"
    })
    assert post_res.status_code == 200
    assert post_res.json()["decision"] == "approved"
    
    # 3. Reload dashboard and verify approved alert is absent from active alerts
    res2 = client.get("/api/v1/dashboard")
    assert res2.status_code == 200
    updated_alerts = [a["alert"]["id"] for a in res2.json()["alerts"]]
    assert target_id not in updated_alerts, f"Approved alert {target_id} must be absent from active dashboard: {updated_alerts}"
