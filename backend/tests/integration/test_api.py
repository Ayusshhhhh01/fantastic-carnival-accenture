from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def setup_function():
    # Reset demo state before each test
    client.post("/api/v1/reset-demo")


def test_health_and_dashboard_contract():
    assert client.get("/health").status_code == 200
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200
    assert "alerts" in response.json()


def test_missing_alert_is_not_found():
    assert client.get("/api/v1/alerts/unknown").status_code == 404


def test_fresh_demo_shows_all_alerts():
    client.post("/api/v1/reset-demo")
    res = client.get("/api/v1/dashboard")
    assert res.status_code == 200
    alerts = [a["alert"]["id"] for a in res.json()["alerts"]]
    assert len(alerts) == 5, f"Expected 5 active alerts on fresh demo, got {len(alerts)}: {alerts}"


def test_rejected_decision_keeps_alert_active():
    client.post("/api/v1/reset-demo")
    post_res = client.post("/api/v1/alerts/A1/decisions", json={
        "decision": "rejected",
        "persona": "Category Manager",
        "feedback": "Rejected recommendation"
    })
    assert post_res.status_code == 200
    assert post_res.json()["decision"] == "rejected"

    res = client.get("/api/v1/dashboard")
    assert res.status_code == 200
    alerts = [a["alert"]["id"] for a in res.json()["alerts"]]
    assert "A1" in alerts, f"Rejected alert A1 must remain active on dashboard queue: {alerts}"


def test_approve_removes_alert_from_active_dashboard_and_persists():
    client.post("/api/v1/reset-demo")
    # 1. Approve alert A1
    post_res = client.post("/api/v1/alerts/A1/decisions", json={
        "decision": "approved",
        "persona": "Category Manager",
        "feedback": "Approved in regression test"
    })
    assert post_res.status_code == 200
    assert post_res.json()["decision"] == "approved"

    # 2. Reload dashboard and verify A1 is absent from active alerts while others remain
    res = client.get("/api/v1/dashboard")
    assert res.status_code == 200
    alerts = [a["alert"]["id"] for a in res.json()["alerts"]]
    assert "A1" not in alerts, f"Approved alert A1 must be absent from active dashboard: {alerts}"
    assert len(alerts) == 4, f"Expected 4 active alerts remaining, got {len(alerts)}: {alerts}"

    # 3. Reload again to verify persistence
    res_reload = client.get("/api/v1/dashboard")
    assert res_reload.status_code == 200
    reload_alerts = [a["alert"]["id"] for a in res_reload.json()["alerts"]]
    assert "A1" not in reload_alerts


def test_multiple_decisions_rejected_then_approved():
    client.post("/api/v1/reset-demo")
    # Step 1: Reject A2
    client.post("/api/v1/alerts/A2/decisions", json={
        "decision": "rejected",
        "persona": "CXO",
        "feedback": "First rejected"
    })
    res1 = client.get("/api/v1/dashboard")
    assert "A2" in [a["alert"]["id"] for a in res1.json()["alerts"]]

    # Step 2: Subsequently approve A2
    client.post("/api/v1/alerts/A2/decisions", json={
        "decision": "approved",
        "persona": "CXO",
        "feedback": "Later approved"
    })
    res2 = client.get("/api/v1/dashboard")
    assert "A2" not in [a["alert"]["id"] for a in res2.json()["alerts"]]


def test_demo_reset_restores_initial_alerts():
    # Approve multiple alerts
    client.post("/api/v1/alerts/A1/decisions", json={"decision": "approved", "persona": "CXO"})
    client.post("/api/v1/alerts/A2/decisions", json={"decision": "approved", "persona": "CXO"})

    # Reset demo
    reset_res = client.post("/api/v1/reset-demo")
    assert reset_res.status_code == 200

    # Verify all 5 alerts restored
    res = client.get("/api/v1/dashboard")
    alerts = [a["alert"]["id"] for a in res.json()["alerts"]]
    assert len(alerts) == 5, f"Expected 5 alerts after demo reset, got: {alerts}"
