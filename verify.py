"""Headless verification of all demo scenarios (no UI)."""
import json
from cause.engine import run, redact_for_cxo
from cause import llm

P = run()
alerts = P["alerts"]

print("=" * 78)
for a in alerts:
    al = a["alert"]
    print(f"{al['id']} | {al['kpi']:15s} | {al['category']}/{al['region']}"
          f" | {al['delta_fmt']} ({al['pct_fmt']}, z={al['z_fmt']})"
          f" -> route={a['route']}")

print("=" * 78)
for a in alerts:
    print(f"\n### {a['alert']['id']} — {a['route']} — "
          f"{a['alert']['category']}/{a['alert']['region']}")
    if a["route"] == "ABSTAIN":
        print("  ", a["abstention"]["message"])
        print("   confidence:", json.dumps(a["confidence"]["components"]))
        continue
    for h in a.get("hypotheses", []):
        print(f"    [{'SUP' if h['supported'] else 'REJ'}] {h['name']}: "
              f"{h['deciding_value']}")
    c = a["confidence"]
    print(f"    confidence={c['score']} tier={c['tier']} "
          f"components={json.dumps(c['components'])}")
    cf = a["conflict"]
    if cf["conflict"]:
        print("    CONFLICT A:", cf["signal_a"])
        print("             B:", cf["signal_b"])
    elif a["route"] != "FAST_PATH":
        print("    conflict=False; comparable:",
              json.dumps(cf.get("comparable_cells")))
    print("    REC:", a["recommendation"]["action"][:120])

# narration + self-verify smoke test on the primary alert
print("\n" + "=" * 78)
primary = alerts[0]
for persona in ("Category Manager", "CXO"):
    payload = redact_for_cxo(dict(primary)) if persona == "CXO" else dict(primary)
    text, eng = llm.narrate(payload, persona)
    clean, removed, audit = llm.self_verify(text, payload)
    print(f"\n--- {persona} [{eng}] audit=[{audit}] removed={len(removed)}")
    print(clean[:600])

print("\n--- LEDGER ---")
for r in P["ledger_rows"]:
    print(f"  {r['step']:45s} {r['engine']:14s} {r['latency_ms']:>8}ms  "
          f"{r['note'][:60]}")

# CXO redaction check
cxo = redact_for_cxo(dict(primary))
blob = json.dumps(cxo)
assert "VoltX Pro" not in blob and "P101" not in blob.replace(
    '"product_id": null', ""), "CXO leak!"
print("\nCXO access gate: no SKU fields in redacted JSON ✓")
