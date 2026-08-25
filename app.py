"""
CAUSE — Causal analysis with falsifiable evidence, for BusinessIntelligence.ai
Run:  streamlit run app.py
Optional LLM: set OPENAI_API_KEY (+ optional CAUSE_LLM_MODEL, OPENAI_BASE_URL).
Without a key the app runs in clearly-labelled OFFLINE TEMPLATE MODE.
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from cause.engine import run, fmt_inr, redact_for_cxo, CXO_LOG
from cause import llm

st.set_page_config(page_title="CAUSE", page_icon="🔎", layout="wide")

# ------------------------------------------------------------------ state --
if "pipeline" not in st.session_state:
    st.session_state.pipeline = run()
P = st.session_state.pipeline
ALERTS = P["alerts"]

st.title("CAUSE — Causal Analysis Under Scrutinized Evidence")
st.caption(
    f"Week of **{P['cur_week']}** · every number below is computed by "
    f"deterministic code; the LLM only turns the finished JSON into prose "
    f"(Step 8) and audits its own output (Step 9). "
    + ("LLM: live API" if llm.llm_available()
       else "**LLM: OFFLINE template mode** — no API key found "
            "(`OPENAI_API_KEY`); narration is deterministically assembled "
            "from the same JSON."))

# ---------------------------------------------------------------- sidebar --
with st.sidebar:
    st.header("Material alerts")
    st.markdown("Sorted by **₹ impact**, not % (materiality = statistical "
                "significance × business impact).")
    labels = []
    for a in ALERTS:
        icon = {"ABSTAIN": "🚫", "UNRESOLVED_CONFLICT": "⚠️",
                "RESOLVED": "✅", "FAST_PATH": "⚡"}.get(a.get("route"), "")
        al = a["alert"]
        labels.append(f"{icon} {al['id']} · {al['category']} / {al['region']}"
                      f" · {al['delta_fmt']}")
    idx = st.radio("Select an alert", range(len(ALERTS)),
                   format_func=lambda i: labels[i], label_visibility="collapsed")

    st.divider()
    if st.button("Regenerate synthetic data & rerun"):
        from cause import data_gen
        s = data_gen.build_sales()
        s.to_csv("cause/data/sales_daily.csv", index=False)
        data_gen.build_campaigns(s).to_csv("cause/data/campaigns_weekly.csv",
                                           index=False)
        data_gen.build_inventory(s).to_csv("cause/data/inventory_daily.csv",
                                           index=False)
        data_gen.build_change_log().to_csv("cause/data/change_log.csv",
                                           index=False)
        st.cache_clear()
        st.session_state.pipeline = run()
        st.rerun()

A = ALERTS[idx]
route = A["route"]

route_banner = {
    "FAST_PATH": ("success", "⚡ FAST PATH — direct match in ops change log"),
    "RESOLVED": ("success", "✅ RESOLVED — winning hypothesis survived "
                            "falsification"),
    "UNRESOLVED_CONFLICT": ("warning", "⚠️ UNRESOLVED — flagged for review: "
                                       "evidence contradicts itself across "
                                       "regions"),
    "ABSTAIN": ("error", "🚫 ABSTAINED — insufficient evidence; the LLM was "
                         "NOT called"),
}[route]

# ------------------------------------------------------------- TWO PANELS --
left, right = st.columns([1.15, 1], gap="large")

# ------------------------------- LEFT: EVIDENCE ----------------------------
with left:
    st.subheader("Evidence (deterministic)")
    kind, msg = route_banner
    getattr(st, kind)(msg)

    a = A["alert"]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(f"{a['kpi']} — {a['week_start']}", a["current_fmt"],
              f"{a['pct_fmt']}")
    m2.metric("Baseline (4-wk)", a["baseline_fmt"])
    m3.metric("Δ impact", a["delta_fmt"])
    m4.metric("z-score vs baseline", a["z_fmt"])
    st.caption(f"Detection rule: |z| ≥ 1.5 AND |Δ| ≥ 10% → material. "
               f"Baseline weeks available: {a['baseline_weeks']}. "
               f"Alert ID {a['id']}, ranked #{idx+1} by absolute rupee "
               f"impact.")

    st.divider()

    if route == "ABSTAIN":
        st.error("**Abstention — LLM deliberately not called**\n\n"
                 + A["abstention"]["message"])
        c = A["confidence"]
        st.write(f"Composite confidence **{c['score']:.2f} (Low)** · "
                 f"components: " + " · ".join(
                     f"{k} `{v}`" for k, v in c["components"].items()))
        st.progress(min(c["score"], 1.0))

    elif route == "FAST_PATH":
        fp = A["fast_path"]
        st.success(f"**Direct change-log match** — event on "
                   f"{fp['event_date']}: *{fp['description']}* "
                   f"(type: {fp['event_type']}, window {fp['window']}). "
                   "Skipped deep hypothesis testing: cheap, fast, "
                   "explainable.")
        c = A["confidence"]
        st.write(f"Confidence **{c['tier']}** ({c['score']:.2f})")

    else:
        st.markdown("##### Competing hypotheses — tested & falsified")
        st.caption("Every hypothesis is checked against real data with a "
                   "real method. Rejected ones stay visible, with the exact "
                   "number that killed them.")
        for h in A["hypotheses"]:
            ok = h["supported"]
            with st.container(border=True):
                head = st.columns([0.72, 0.28])
                head[0].markdown(f"**{h['name']}**")
                head[1].markdown(
                    ":green-badge[SUPPORTED]" if ok
                    else ":red-badge[REJECTED]")
                st.write(f"{h['verdict']}")
                st.caption(f"Deciding metric: {h['deciding_metric']} → "
                           f"**{h['deciding_value']}**\n\n"
                           f"Source: {h['data_source']}")

        st.divider()
        c = A["confidence"]
        tier_color = {"High": "green", "Medium": "orange", "Low": "red"}[
            c["tier"]]
        st.markdown(
            f"##### Confidence — **{c['tier']}** ({c['score']:.2f}) "
            f":{tier_color}-badge[{c['tier']}]")
        cc1, cc2 = st.columns(2)
        for i, (k, v) in enumerate(c["components"].items()):
            (cc1 if i < 2 else cc2).write(f"{k.replace('_', ' ')}: `{v}`")
        st.progress(min(c["score"], 1.0))
        st.caption("Weighted: temporal .30 · source agreement .25 · "
                   "completeness .25 · hypothesis margin .20")

        cf = A["conflict"]
        if cf["conflict"]:
            st.warning("**Conflict check — CONTRADICTION**\n\n"
                       f"- Signal A: {cf['signal_a']}\n"
                       f"- Signal B: {cf['signal_b']}")
        else:
            st.info("Conflict check: comparable regions with similar "
                    "exposure show consistent outcomes — no contradiction."
                    + (f" Checked: {json.dumps(cf['comparable_cells'])}"
                       if cf.get("comparable_cells") else ""))

    rec = A["recommendation"]
    st.divider()
    st.markdown("##### Recommended action")
    st.write(f"**{rec['action']}**")
    if rec.get("est_impact_fmt"):
        st.write(f"Estimated impact: **{rec['est_impact_fmt']} / week** — "
                 f"basis: {rec['basis']}")
    else:
        st.caption(f"Basis: {rec['basis']}")

# ----------------------------- RIGHT: EXPLANATION --------------------------
with right:
    st.subheader("Explanation (LLM)")
    persona = st.radio("Persona", ["Category Manager", "CXO"],
                       horizontal=True,
                       help="CXO sees category aggregates only; SKU fields "
                            "are redacted by a deterministic access gate.")

    # Step 7 access gate
    payload = dict(A)
    if persona == "CXO":
        payload = redact_for_cxo(payload)
        st.caption("🔒 " + CXO_LOG[-1])

    cache_key = (a["id"], persona)
    if cache_key not in st.session_state.get("narrations", {}):
        st.session_state.setdefault("narrations", {})
        text, engine_lbl = llm.narrate(payload, persona)
        clean, removed, audit_engine = llm.self_verify(text, payload)
        st.session_state.narrations[cache_key] = {
            "raw": text, "clean": clean, "removed": removed,
            "engine": engine_lbl, "audit_engine": audit_engine}

    N = st.session_state.narrations[cache_key]

    st.caption(f"Generated by: {N['engine']} · audited by: "
               f"{N['audit_engine']} · input to LLM = finished JSON only "
               "(no raw rows)")
    if N["removed"]:
        for r in N["removed"]:
            claim = r.get("claim_sentence") or r.get("claim", "")
            st.warning("⚠️ Unverified claim detected and removed: " + claim)
        st.markdown(N["clean"])
    else:
        st.success("✅ Self-verify pass: every claim traced to a field in "
                   "the source JSON.")
        st.markdown(N["clean"])

    with st.expander("Exact JSON handed to the LLM (after access gate)",
                     expanded=False):
        st.json(json.loads(json.dumps(
            {k: v for k, v in payload.items() if k != "fast_path"},
            default=str)))

# --------------------- BOTTOM: LEDGER + FEEDBACK (always) ------------------
st.divider()
st.subheader("Evidence Ledger — deterministic vs LLM, step by step")
led = pd.DataFrame(P["ledger_rows"] +
                   [{"step": f"Step 8/9 Narration ({persona})",
                     "engine": N["engine"], "latency_ms": None,
                     "est_cost_usd": None,
                     "note": "cached this session"}])
st.dataframe(led, width="stretch", hide_index=True)
l1, l2, l3 = st.columns(3)
l1.metric("Deterministic steps", int(led.engine.str.contains(
    "Deterministic").sum()))
l2.metric("LLM steps", int(led.engine.str.contains("LLM call").sum()))
cost_total = pd.to_numeric(led.est_cost_usd, errors="coerce").fillna(0).sum()
l3.metric("Est. LLM cost (USD)", f"${cost_total:.4f}")

st.divider()
fb1, fb2, fb3, fb4 = st.columns([1, 1, 1.6, 4])
st.markdown("**Analyst decision** — logged to `decisions.csv`; feeds back "
            "into confidence weighting over time.")
clicked = None
if fb1.button("👍 Approve", width="stretch"):
    clicked = "approve"
if fb2.button("👎 Dismiss", width="stretch"):
    clicked = "dismiss"
if fb3.button("🔎 Request more evidence", width="stretch"):
    clicked = "request_more_evidence"
if clicked:
    pd.DataFrame([{**{"alert_id": a["id"], "category": a["category"],
                      "region": a["region"], "decision": clicked},
                   "route": route}]).to_csv(
        Path("cause/data/decisions.csv"), mode="a",
        header=not Path("cause/data/decisions.csv").exists(), index=False)
    st.toast(f"Logged '{clicked}' for {a['id']}", icon="📝")

st.caption("Reconciliation trail: " + " | ".join(A["reconcile_log"]))
