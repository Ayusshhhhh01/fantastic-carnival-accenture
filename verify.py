"""Headless verification of all demo scenarios against Canonical CAUSE Architecture."""
import json
from cause.engine import run, redact_for_cxo, KPI_REGISTRY, EmpiricalFeedbackCalibrator
from cause import llm

P = run()
alerts = P["alerts"]

print("=" * 80)
print("CANONICAL CAUSE VERIFICATION — 10-STEP PIPELINE AUDIT")
print("=" * 80)

# 1. KPI Registry check
assert len(KPI_REGISTRY) == 5, f"Expected 5 connected KPIs, got {len(KPI_REGISTRY)}"
print(f"[✓] Step 1: KPI Semantic Layer defined ({len(KPI_REGISTRY)} connected KPIs across telemetry grains)")

for a in alerts:
    al = a["alert"]
    print(f"  {al['id']} | {al['kpi']:15s} | {al['category']}/{al['region']}"
          f" | {al['delta_fmt']} ({al['pct_fmt']}, z={al['z_fmt']})"
          f" -> route={a['route']}")

print("\n" + "=" * 80)
for a in alerts:
    al = a["alert"]
    print(f"\n### {al['id']} — {a['route']} — {al['category']}/{al['region']}")
    
    # 2. RAG evidence assertion
    assert "rag_evidence" in a, f"Missing RAG evidence in {al['id']}"
    print(f"    [RAG] Retrieved {len(a['rag_evidence'])} multi-source evidence citations")
    
    if a["route"] == "ABSTAIN":
        abst = a["abstention"]
        assert abst.get("abstain_flag") is True
        print("    [ABSTAIN] Reason:", abst["reason"])
        print("              Missing:", abst["missing_data"])
        print("              Required:", abst["required_data"])
        continue
        
    # 3. Top 4 candidate hypotheses assertion for Deep Path
    if a["route"] != "FAST_PATH":
        hyps = a.get("hypotheses", [])
        assert len(hyps) == 4, f"Expected TOP 4 candidate causes, got {len(hyps)}"
        for h in hyps:
            print(f"    [{'SUP' if h['supported'] else 'REJ'}] {h['name']}: "
                  f"{h['confidence_pct']}% · {h['deciding_value'][:70]}")
                  
    # 4. Confidence
    c = a["confidence"]
    print(f"    [CONFIDENCE] {c['score']} tier={c['tier']} components={json.dumps(c['components'])}")
    
    # 5. Conflict check
    cf = a["conflict"]
    if cf["conflict"]:
        assert "signal_a" in cf and "signal_b" in cf and "escalation_directive" in cf
        print("    [CONFLICT A]:", cf["signal_a"])
        print("    [CONFLICT B]:", cf["signal_b"])
        print("    [ESCALATION]:", cf["escalation_directive"])
        
    # 6. 7-Part Recommendation assertion
    rec = a["recommendation"]
    for req_field in ("driver", "lever", "action", "owner", "confidence", "monitoring_plan", "basis"):
        assert req_field in rec, f"Missing {req_field} in recommendation for {al['id']}"
    print(f"    [REC 7-PART]: Driver: {rec['driver'][:40]} | Lever: {rec['lever'][:35]} | Owner: {rec['owner']}")

# Narration + self-verify smoke test on the primary alert
print("\n" + "=" * 80)
primary = alerts[0]
for persona in ("Category Manager", "CXO"):
    payload = redact_for_cxo(dict(primary)) if persona == "CXO" else dict(primary)
    text, eng = llm.narrate(payload, persona)
    clean, removed, audit = llm.self_verify(text, payload)
    word_count = len(clean.split())
    assert 30 <= word_count <= 95, f"Narration word count {word_count} out of range [30..95] for {persona}"
    assert "{" not in clean and "}" not in clean, "Raw JSON syntax found in narration"
    print(f"\n--- {persona} [{eng}] audit=[{audit}] words={word_count} removed={len(removed)}")
    print(clean)

print("\n--- LEDGER ---")
for r in P["ledger_rows"]:
    print(f"  {r['step']:45s} {r['engine']:22s} {r['latency_ms']:>8}ms  {r['note'][:55]}")

# CXO redaction check
cxo = redact_for_cxo(dict(primary))
blob = json.dumps(cxo)
assert "VoltX Pro" not in blob and "P101" not in blob.replace('"product_id": null', ""), "CXO leak!"
print("\n[✓] CXO access gate: zero SKU leakage in redacted JSON & citations")

# Calibrator smoke check
calibrator = EmpiricalFeedbackCalibrator()
assert 0.85 <= calibrator.get_calibration_factor("Supply", "Electronics") <= 1.05
print("[✓] Empirical Feedback Calibrator active")

print("\nALL CANONICAL CAUSE VERIFICATION CHECKS PASSED (100% COMPLIANT) ✓")

