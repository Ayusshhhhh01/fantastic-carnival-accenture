import pytest
import pandas as pd
from pathlib import Path
from cause.engine import fast_path_check, EmpiricalFeedbackCalibrator, attach_hypothesis_confidence, HYP_WEIGHTS


def test_fast_path_regional_vs_aggregate():
    """Verify Fast Path matching behavior for regional vs aggregate (all) alerts."""
    # Mock change log data
    changelog_df = pd.DataFrame([
        {
            "date": pd.Timestamp("2026-08-10"),
            "category": "Snacks",
            "region": "North",
            "event_type": "operational",
            "description": "DC conveyor outage"
        },
        {
            "date": pd.Timestamp("2026-08-11"),
            "category": "Beverages",
            "region": "South",
            "event_type": "campaign",
            "description": "CRM Summer Promo launch"
        }
    ])

    # 1. Regional alert (Snacks / South) -> should NOT match North event
    reg_alert_no_match = {
        "category": "Snacks",
        "region": "South",
        "week_start": pd.Timestamp("2026-08-10")
    }
    result_reg_no_match, _ = fast_path_check(reg_alert_no_match, changelog_df)
    assert result_reg_no_match is None

    # 2. Regional alert (Snacks / North) -> SHOULD match North event
    reg_alert_match = {
        "category": "Snacks",
        "region": "North",
        "week_start": pd.Timestamp("2026-08-10")
    }
    result_reg_match, _ = fast_path_check(reg_alert_match, changelog_df)
    assert result_reg_match is not None
    assert result_reg_match["matched"] is True
    assert result_reg_match["event_type"] == "operational"

    # 3. Aggregate "(all)" alert (Beverages / (all)) -> SHOULD discover South event
    agg_alert_match = {
        "category": "Beverages",
        "region": "(all)",
        "week_start": pd.Timestamp("2026-08-10")
    }
    result_agg_match, _ = fast_path_check(agg_alert_match, changelog_df)
    assert result_agg_match is not None
    assert result_agg_match["matched"] is True
    assert result_agg_match["event_type"] == "campaign"
    assert result_agg_match["region"] == "South"


def test_hypothesis_specific_feedback_calibration(tmp_path):
    """Verify hypothesis-specific calibration factors and confidence clamping."""
    decisions_csv = tmp_path / "decisions.csv"

    # Create historical decisions: 4 Supply rejections and 4 Pricing approvals
    decisions_df = pd.DataFrame([
        {"alert_id": "A1", "category": "Snacks", "hypothesis_type": "Supply", "decision": "rejected"},
        {"alert_id": "A2", "category": "Snacks", "hypothesis_type": "Supply", "decision": "rejected"},
        {"alert_id": "A3", "category": "Snacks", "hypothesis_type": "Supply", "decision": "rejected"},
        {"alert_id": "A4", "category": "Snacks", "hypothesis_type": "Supply", "decision": "rejected"},
        {"alert_id": "A5", "category": "Snacks", "hypothesis_type": "Pricing", "decision": "approved"},
        {"alert_id": "A6", "category": "Snacks", "hypothesis_type": "Pricing", "decision": "approved"},
        {"alert_id": "A7", "category": "Snacks", "hypothesis_type": "Pricing", "decision": "approved"},
        {"alert_id": "A8", "category": "Snacks", "hypothesis_type": "Pricing", "decision": "approved"},
    ])
    decisions_df.to_csv(decisions_csv, index=False)

    calibrator = EmpiricalFeedbackCalibrator(decisions_path=decisions_csv)

    # 1. Supply rejections should lower Supply factor (factor = 0.90)
    supply_factor = calibrator.get_calibration_factor("Supply", "Snacks")
    assert supply_factor == 0.90

    # 2. Pricing approvals should increase Pricing factor (factor = 1.05)
    pricing_factor = calibrator.get_calibration_factor("Pricing", "Snacks")
    assert pricing_factor == 1.05

    # 3. Demand has zero history -> should return default factor 1.00
    demand_factor = calibrator.get_calibration_factor("Demand", "Snacks")
    assert demand_factor == 1.00

    # 4. Attach hypothesis confidence with calibrator & test clamping
    hyps = [
        {"name": "Supply-side (stock-out)", "supported": True, "score": 0.95},
        {"name": "Pricing change", "supported": True, "score": 0.98}
    ]
    comps = {
        "temporal_correlation": 1.0,
        "source_agreement": 1.0,
        "hypothesis_margin": 0.5,
        "data_completeness": 1.0
    }

    attach_hypothesis_confidence(hyps, comps, calibrator=calibrator, category="Snacks")

    for h in hyps:
        # Confidence must be bounded between 0 and 100%
        assert 0 <= h["confidence_pct"] <= 100

    # Supply confidence should be reduced by 0.90 factor
    supply_hyp = next(h for h in hyps if "Supply" in h["name"])
    assert supply_hyp["confidence_pct"] < 95


def test_old_decisions_csv_backwards_compatibility(tmp_path):
    """Verify calibrator handles old decisions CSV missing hypothesis_type column."""
    decisions_csv = tmp_path / "old_decisions.csv"

    # Old CSV format without hypothesis_type column
    old_df = pd.DataFrame([
        {"alert_id": "A1", "category": "Beverages", "decision": "approved"},
        {"alert_id": "A2", "category": "Beverages", "decision": "rejected"},
    ])
    old_df.to_csv(decisions_csv, index=False)

    calibrator = EmpiricalFeedbackCalibrator(decisions_path=decisions_csv)
    factor = calibrator.get_calibration_factor("Supply", "Beverages")
    # Under 3 reviews -> returns 1.0 safely without crashing
    assert factor == 1.0


def test_dashboard_contains_all_5_kpi_types():
    """Verify AnalysisService dashboard contains all 5 KPI types and fails if only Revenue+Marketing Spend exist."""
    from backend.app.services.analysis_service import AnalysisService
    service = AnalysisService()
    dash = service.dashboard(refresh=True, persona="Category Manager")
    alerts = dash.get("alerts", [])
    kpi_set = {a["alert"]["kpi"] for a in alerts}

    expected_kpis = {"Revenue", "Marketing Spend", "Units Sold", "Average Realized Price", "Stockout Incident Days"}
    missing = expected_kpis - kpi_set
    assert not missing, f"Dashboard missing KPI types: {missing}. Present KPIs: {kpi_set}"
    assert len(kpi_set) == 5, f"Expected 5 KPI types on dashboard, got {len(kpi_set)}: {kpi_set}"


def test_persona_ordering_differs_between_category_manager_and_cxo():
    """Verify that Category Manager and CXO personas order the SAME underlying alert pool differently."""
    from backend.app.services.analysis_service import AnalysisService
    service = AnalysisService()

    cm_dash = service.dashboard(refresh=True, persona="Category Manager")
    cxo_dash = service.dashboard(refresh=True, persona="CXO")

    cm_ids = [a["alert"]["id"] for a in cm_dash.get("alerts", [])]
    cxo_ids = [a["alert"]["id"] for a in cxo_dash.get("alerts", [])]

    # Same set of alert IDs
    assert set(cm_ids) == set(cxo_ids)

    # Different ordering
    assert cm_ids != cxo_ids, "Category Manager and CXO must have different alert ordering based on persona lens!"

    # Category Manager top KPI should be an operational KPI (Units Sold / Stockout Incident Days / Average Realized Price)
    cm_top_kpi = cm_dash["alerts"][0]["alert"]["kpi"]
    assert cm_top_kpi in ("Units Sold", "Stockout Incident Days", "Average Realized Price"), f"Category Manager top KPI should be operational, got: {cm_top_kpi}"
