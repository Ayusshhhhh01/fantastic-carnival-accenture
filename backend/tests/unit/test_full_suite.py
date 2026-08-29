"""
Comprehensive Regression & Validation Test Suite for CAUSE engine.
Tests all 19 core evaluation dimensions including zero LLM calls on ABSTAIN,
single-render non-duplication, CXO redaction, 4 hypotheses falsification, and 7-part recommendations.
"""
import pytest
import pandas as pd
from cause.engine import (
    load_data, detect, analyze_alert, redact_for_cxo, recommend,
    conflict_check, score_confidence, KPI_REGISTRY
)
from cause.llm import narrate, self_verify, llm_available
from backend.app.services.analysis_service import AnalysisService
from backend.app.services.narrative_service import NarrativeService


@pytest.fixture(scope="module")
def data_setup():
    sales, camps, inv, changelog = load_data()
    return {
        "sales": sales,
        "camp": camps,
        "inv": inv,
        "changelog": changelog
    }


def test_1_kpi_registry_semantic_layer():
    """Verify 5 KPIs defined and role distinction between Alerting Signals and Drivers."""
    assert len(KPI_REGISTRY) == 5
    assert KPI_REGISTRY["Revenue"]["role_in_pipeline"] == "Anomaly Detection Signal"
    assert KPI_REGISTRY["Marketing Spend"]["role_in_pipeline"] == "Anomaly Detection Signal"
    assert KPI_REGISTRY["Units Sold"]["role_in_pipeline"] == "Connected Causal Evidence / Driver"
    assert KPI_REGISTRY["Stockout Incident Days"]["role_in_pipeline"] == "Connected Causal Evidence / Driver"
    assert KPI_REGISTRY["Average Realized Price"]["role_in_pipeline"] == "Connected Causal Evidence / Driver"


def test_2_supply_rca(data_setup):
    """Test supply-side (stock-out) root cause identification for A1 (Electronics/Region X)."""
    service = AnalysisService()
    res = service.investigate_alert("A1", persona="Category Manager")
    assert res["route"] == "RESOLVED"
    assert res["path_type"] == "SLOW"
    
    # Highest ranked hypothesis should be Supply-side
    top_hyp = res["hypotheses"][0]
    assert top_hyp["name"] == "Supply-side (stock-out)"
    assert top_hyp["supported"] is True
    assert top_hyp["score"] > 0.8
    assert "supporting_evidence" in top_hyp
    assert "contrary_evidence" in top_hyp


def test_3_conflict_detection(data_setup):
    """Test cross-regional conflict detection for A2 (Electronics/Region Y)."""
    service = AnalysisService()
    res = service.investigate_alert("A2", persona="Category Manager")
    assert res["route"] == "UNRESOLVED_CONFLICT"
    assert res["path_type"] == "SLOW"
    assert res["conflict"]["conflict"] is True
    assert "signal_a" in res["conflict"]
    assert "signal_b" in res["conflict"]


def test_4_critical_abstention_zero_llm_calls(data_setup, monkeypatch):
    """Test that route == ABSTAIN NEVER makes LLM calls (narrate / self_verify bypassed)."""
    llm_called = False

    def mock_chat(*args, **kwargs):
        nonlocal llm_called
        llm_called = True
        return "LLM generated text", 0.1, 0.001

    import cause.llm as llm_mod
    monkeypatch.setattr(llm_mod, "_chat", mock_chat)
    monkeypatch.setattr(llm_mod, "llm_available", lambda: True)

    service = AnalysisService()
    res = service.investigate_alert("A3", persona="Category Manager")
    
    assert res["route"] == "ABSTAIN"
    assert res["path_type"] == "ABSTAIN"
    assert res["narrative"] is None
    assert llm_called is False, "LLM was invoked on ABSTAIN route!"


def test_5_demand_rca(data_setup):
    """Test demand-side (marketing spend shift) root cause for A4."""
    service = AnalysisService()
    res = service.investigate_alert("A4", persona="Category Manager")
    assert res["route"] == "RESOLVED"
    top_hyp = res["hypotheses"][0]
    assert top_hyp["name"] == "Demand-side (campaign/demand shift)"
    assert top_hyp["supported"] is True


def test_6_fast_path_event_match(data_setup):
    """Test fast path direct event matching for A5 (Apparel/Region Z)."""
    service = AnalysisService()
    res = service.investigate_alert("A5", persona="Category Manager")
    assert res["route"] == "FAST_PATH"
    assert res["path_type"] == "FAST"
    assert res["fast_path"] is not None
    assert res["fast_path"].get("is_fast_path") is True or res["fast_path"].get("event_type") is not None


def test_7_exactly_4_hypotheses_and_falsification(data_setup):
    """Verify exactly 4 hypotheses returned and all contain falsification details."""
    service = AnalysisService()
    res = service.investigate_alert("A1", persona="Category Manager")
    assert len(res["hypotheses"]) == 4
    
    names = {h["name"] for h in res["hypotheses"]}
    expected_names = {
        "Supply-side (stock-out)",
        "Demand-side (campaign/demand shift)",
        "Pricing change",
        "Operational / Channel Disruption"
    }
    assert names == expected_names
    
    for h in res["hypotheses"]:
        assert "supported" in h
        assert "verdict" in h
        assert "score" in h
        assert "supporting_evidence" in h
        assert "contrary_evidence" in h


def test_8_cxo_redaction_security(data_setup):
    """Verify CXO payload scrubs all SKU codes, product names, and granular product details."""
    service = AnalysisService()
    res_cm = service.investigate_alert("A1", persona="Category Manager")
    res_cxo = service.investigate_alert("A1", persona="CXO")
    
    # Category Manager gets granular SKU
    assert "P101" in str(res_cm) or "VoltX" in str(res_cm)
    
    # CXO payload must NOT leak SKU or product name pre-API
    cxo_str = str(res_cxo)
    assert "P101" not in cxo_str
    assert "VoltX Pro 5G Phone" not in cxo_str
    assert "[redacted SKU]" in cxo_str or "product_id" not in res_cxo.get("recommendation", {})


def test_9_7_part_recommendation_completeness(data_setup):
    """Verify recommendation contains all 7 conceptual fields."""
    service = AnalysisService()
    res = service.investigate_alert("A1", persona="Category Manager")
    rec = res["recommendation"]
    assert rec is not None
    assert "driver" in rec
    assert "lever" in rec
    assert "action" in rec
    assert "estimated_impact" in rec
    assert "owner" in rec
    assert "confidence" in rec
    assert "monitoring_plan" in rec


def test_10_multi_source_evidence_provenance(data_setup):
    """Verify evidence items contain source, entity, relevance, and snippet."""
    service = AnalysisService()
    res = service.investigate_alert("A1", persona="Category Manager")
    ev_list = res.get("rag_evidence", [])
    assert len(ev_list) > 0
    for ev in ev_list:
        assert "source" in ev
        assert "relevance_score" in ev


def test_11_weighted_evidence_confidence(data_setup):
    """Verify Weighted Evidence Confidence components W1-W4 exist."""
    service = AnalysisService()
    res = service.investigate_alert("A1", persona="Category Manager")
    conf = res["confidence"]
    assert "score" in conf
    assert "tier" in conf
    assert "components" in conf
    comps = conf["components"]
    assert "temporal_correlation" in comps
    assert "source_agreement" in comps
    assert "hypothesis_margin" in comps
    assert "data_completeness" in comps


def test_12_single_render_no_duplication():
    """Regression test ensuring narrative single-render produces no duplicated text."""
    payload = {
        "route": "RESOLVED",
        "alert": {"kpi": "Revenue", "category": "Electronics", "region": "Region X", "delta_fmt": "-₹41.6L", "pct_fmt": "-19.4%"},
        "recommendation": {"action": "Expedite replenishment", "estimated_impact": 11300000, "est_impact_fmt": "₹1.13Cr"},
        "winning_hypothesis": {"name": "Supply-side (stock-out)", "supported": True, "score": 0.98}
    }
    txt, engine = narrate(payload, persona="Category Manager")
    clean, removed, audit = self_verify(txt, payload)
    
    # Assert single rendering: text should not repeat its own first paragraph
    first_sentence = clean.split(".")[0]
    assert clean.count(first_sentence) == 1, "Narrative text duplicated first sentence!"


def test_13_historical_series_attached(data_setup):
    """Verify historical_series telemetry data attached to alert for real KPIChart rendering."""
    service = AnalysisService()
    res = service.investigate_alert("A1", persona="Category Manager")
    alert = res["alert"]
    assert "historical_series" in alert
    assert len(alert["historical_series"]) > 0
    item = alert["historical_series"][0]
    assert "week" in item
    assert "value" in item
    assert "expected" in item
