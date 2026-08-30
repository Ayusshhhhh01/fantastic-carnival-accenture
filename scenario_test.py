"""End-to-end scenario test verifying all 5 retail scenarios and canonical requirements."""
import json
from cause.engine import run, redact_for_cxo, KPI_REGISTRY, EmpiricalFeedbackCalibrator
from cause import llm

def test_canonical_pipeline():
    P = run()
    alerts = {a["alert"]["id"]: a for a in P["alerts"]}
    
    # 1. KPI Registry checks
    assert len(KPI_REGISTRY) == 5
    assert KPI_REGISTRY["Revenue"]["role_in_pipeline"] == "Anomaly Detection Signal"
    assert KPI_REGISTRY["Marketing Spend"]["role_in_pipeline"] == "Anomaly Detection Signal"
    assert KPI_REGISTRY["Units Sold"]["role_in_pipeline"] == "Connected Causal Evidence / Driver"
    assert KPI_REGISTRY["Stockout Incident Days"]["role_in_pipeline"] == "Connected Causal Evidence / Driver"
    assert KPI_REGISTRY["Average Realized Price"]["role_in_pipeline"] == "Connected Causal Evidence / Driver"
    print("[✓] KPI Semantic Layer: 5 connected KPIs properly distinguished (signals vs drivers)")

    # 2. Scenario A1: Deep Path Happy Path (Electronics / Region X - Stockout)
    a1 = alerts["A1"]
    assert a1["route"] == "RESOLVED"
    assert a1["fast_path"] is None
    assert len(a1["hypotheses"]) == 4
    winner = next(h for h in a1["hypotheses"] if h["supported"])
    assert winner["name"] == "Supply-side (stock-out)"
    assert winner["confidence_pct"] >= 85
    assert a1["conflict"]["conflict"] is False
    rec1 = a1["recommendation"]
    assert "driver" in rec1 and "lever" in rec1 and "monitoring_plan" in rec1
    
    # Check concise narration
    cm_text, _ = llm.narrate(a1, "Category Manager")
    cxo_text, _ = llm.narrate(redact_for_cxo(dict(a1)), "CXO")
    assert 30 <= len(cm_text.split()) <= 95, f"CM text words: {len(cm_text.split())}"
    assert 25 <= len(cxo_text.split()) <= 80, f"CXO text words: {len(cxo_text.split())}"
    assert "VoltX Pro" in cm_text
    assert "VoltX Pro" not in cxo_text and "P101" not in cxo_text
    print("[✓] Scenario A1: Deep Path verified with concise executive copy & CXO redaction")

    # 3. Scenario A2: Unresolved Conflict (Electronics / Region Y)
    a2 = alerts["A2"]
    assert a2["route"] == "UNRESOLVED_CONFLICT"
    assert a2["conflict"]["conflict"] is True
    assert a2["conflict"]["signal_a"] and a2["conflict"]["signal_b"]
    assert "escalation_directive" in a2["conflict"]
    cm2_text, _ = llm.narrate(a2, "Category Manager")
    assert "Contradiction" in cm2_text or "manual audit" in cm2_text
    print("[✓] Scenario A2: Unresolved Conflict flagged with Signal A & Signal B")

    # 4. Scenario A3: Abstention (Wearables / Region Z - Sparse Data)
    a3 = alerts["A3"]
    assert a3["route"] == "ABSTAIN"
    assert a3["abstention"]["abstain_flag"] is True
    assert "missing_data" in a3["abstention"] and "required_data" in a3["abstention"]
    print("[✓] Scenario A3: Abstention verified with explicit telemetry gaps")

    # 5. Scenario A4: Demand-side Resolution (Electronics / all)
    a4 = alerts["A4"]
    assert a4["route"] == "RESOLVED"
    w4 = next(h for h in a4["hypotheses"] if h["supported"])
    assert w4["name"].startswith("Demand")
    print("[✓] Scenario A4: Marketing campaign spike resolved")

    # 6. Scenario A5: Fast Path Direct Event Match (Apparel / Region Z)
    a5 = alerts["A5"]
    assert a5["route"] == "FAST_PATH"
    assert a5["fast_path"] is not None
    assert a5["fast_path"]["event_type"] == "it_incident"
    assert len(a5["hypotheses"]) == 0
    print("[✓] Scenario A5: Fast Path direct match verified (bypasses deep analysis)")

    # 7. Feedback Calibration
    calibrator = EmpiricalFeedbackCalibrator()
    factor = calibrator.get_calibration_factor("Supply", "Electronics")
    assert factor in (0.90, 1.00)
    print("[✓] Empirical Feedback Calibration active")

    print("\nALL SCENARIOS PASSED 100%!")

if __name__ == "__main__":
    test_canonical_pipeline()
