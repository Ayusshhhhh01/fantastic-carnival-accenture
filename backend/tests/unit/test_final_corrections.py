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


def test_persona_kpi_portfolios_are_distinct():
    """Verify AnalysisService returns genuinely distinct KPI alert portfolios for Category Manager vs CXO."""
    from backend.app.services.analysis_service import AnalysisService
    service = AnalysisService()

    cm_dash = service.dashboard(refresh=True, persona="Category Manager")
    cxo_dash = service.dashboard(refresh=True, persona="CXO")

    cm_kpis = {a["alert"]["kpi"] for a in cm_dash.get("alerts", [])}
    cxo_kpis = {a["alert"]["kpi"] for a in cxo_dash.get("alerts", [])}

    # Verify Category Manager KPI portfolio contains operational/commercial KPIs
    expected_cm_kpis = {"Units Sold", "Stockout Incident Days", "Average Realized Price", "Category Revenue", "Campaign Promotional Effectiveness"}
    assert cm_kpis.issubset(expected_cm_kpis), f"Category Manager alerts contain unexpected KPIs: {cm_kpis - expected_cm_kpis}"
    assert "Revenue" not in cm_kpis, "Category Manager dashboard must not contain generic 'Revenue'!"
    assert "Marketing Spend" not in cm_kpis, "Category Manager dashboard must not contain generic 'Marketing Spend'!"

    # Verify CXO KPI portfolio contains executive/financial KPIs
    expected_cxo_kpis = {"Enterprise Revenue", "Marketing Efficiency", "Price Pressure", "Inventory Risk", "Portfolio Performance", "Portfolio Strategic Risk"}
    assert cxo_kpis.issubset(expected_cxo_kpis), f"CXO alerts contain unexpected KPIs: {cxo_kpis - expected_cxo_kpis}"

    # Verify KPI portfolios do not overlap
    overlap = cm_kpis.intersection(cxo_kpis)
    assert not overlap, f"Category Manager and CXO KPI portfolios must not share identical KPI names! Overlap: {overlap}"


def test_shared_rca_engine_preserves_analytical_truth():
    """Verify investigating a signal returns identical RCA evidence regardless of persona framing."""
    from backend.app.services.analysis_service import AnalysisService
    service = AnalysisService()

    cm_investigation = service.investigate_alert("A1", persona="Category Manager")
    cxo_investigation = service.investigate_alert("A1", persona="CXO")

    # Analytical truth (hypotheses, confidence score, conflict state, route) must be 100% identical
    assert cm_investigation["route"] == cxo_investigation["route"]
    assert cm_investigation["confidence"]["score"] == cxo_investigation["confidence"]["score"]
    assert len(cm_investigation["hypotheses"]) == len(cxo_investigation["hypotheses"])

    for cm_h, cxo_h in zip(cm_investigation["hypotheses"], cxo_investigation["hypotheses"]):
        assert cm_h["name"] == cxo_h["name"]
        assert cm_h["score"] == cxo_h["score"]
        assert cm_h["supported"] == cxo_h["supported"]
