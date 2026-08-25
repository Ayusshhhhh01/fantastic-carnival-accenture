"""
CAUSE — guided step-through analysis flow.
Run:  streamlit run app.py
Optional LLM: set OPENAI_API_KEY (+ optional CAUSE_LLM_MODEL, OPENAI_BASE_URL).
Without a key narration runs in clearly-labelled OFFLINE TEMPLATE MODE.

UI model: clicking an alert opens a sequential reveal. Each pipeline step
appears only after the previous one, with a visible computation moment,
stacking downward like a growing log. Steps 5 and 6 are branch points where
the flow visibly HALTS (abstention / conflict) — the LLM is never called.
"""
import json
import time
from pathlib import Path

import pandas as pd
import streamlit as st

from cause.engine import run, redact_for_cxo, CXO_LOG, fmt_inr
from cause import llm

st.set_page_config(page_title="CAUSE", page_icon="🔎", layout="wide")

ss = st.session_state
ss.setdefault("pipeline", run())
ss.setdefault("view", "list")
ss.setdefault("alert_idx", None)
ss.setdefault("step_pos", 0)
ss.setdefault("persona", "Category Manager")
ss.setdefault("animated", set())          # keys of animations already played
ss.setdefault("narrations", {})           # (alert_id, persona) -> narration

P = ss["pipeline"]
ALERTS = P["alerts"]

# step order per route; halts happen because the list simply ends there
ORDER = {
    "RESOLVED": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    "FAST_PATH": [1, 2, 3, 6, 7, 8, 9, 10],
    "UNRESOLVED_CONFLICT": [1, 2, 3, 4, 5, 6],
    "ABSTAIN": [1, 2, 3, 4, 5],
}
NEXT_LABEL = {
    1: "Investigate →",
    2: "Check Fast Path →",
    3: "Run Deep Path →",
    4: "Calculate Confidence →",
    5: "Check for Conflicts →",
    6: "Check Access Permissions →",
    7: "Generate Explanation →",
    8: "Verify Claims →",
    9: "See Recommendation →",
}
STEP_TITLE = {
    1: "Alert Summary", 2: "Reconciliation", 3: "Fast Path Check",
    4: "Hypothesis Testing", 5: "Confidence Score", 6: "Conflict Check",
    7: "Access Gate", 8: "Narration", 9: "Self-Verification",
    10: "Recommendation",
}


def animate(key, msg, delay=0.8):
    """Play a computation moment exactly once per (alert, step)."""
    if key not in ss["animated"]:
        with st.spinner(msg):
            time.sleep(delay)
        ss["animated"].add(key)


def open_alert(i):
    aid = ALERTS[i]["alert"]["id"]
    ss["view"] = "detail"
    ss["alert_idx"] = i
    ss["step_pos"] = 0
    for k in list(ss["animated"]):
        if isinstance(k, tuple) and k[0] == aid:
            ss["animated"].remove(k)
    st.rerun()


# ============================================================ LIST VIEW ====
if ss["view"] == "list":
    st.title("CAUSE — Causal Analysis Under Scrutinized Evidence")
    llm_mode = ("🟢 Live LLM" if llm.llm_available()
                else "🟡 Offline template mode (no OPENAI_API_KEY)")
    st.caption(f"Pipeline week {P['cur_week']} · engine: {llm_mode} · "
               "every number computed by deterministic code; the LLM only "
               "narrates finished JSON (Step 8) and audits itself (Step 9).")

    st.subheader(f"Material alerts — week of {P['cur_week']}")
    st.markdown("Sorted by **₹ impact**, not %. Materiality = statistical "
                "significance (|z| ≥ 1.5) × business impact (|Δ| ≥ 10%). "
                "Select an alert to watch the pipeline reason through it "
                "step by step.")

    icon_map = {"ABSTAIN": "🚫 ABSTAINED", "UNRESOLVED_CONFLICT":
                "⚠️ UNRESOLVED CONFLICT", "RESOLVED": "✅ RESOLVED",
                "FAST_PATH": "⚡ FAST PATH"}
    rows = []
    for a in ALERTS:
        al = a["alert"]
        rows.append({
            "Alert": al["id"], "KPI": al["kpi"],
            "Category / Region": f"{al['category']} / {al['region']}",
            "Δ impact": al["delta_fmt"], "% dev": al["pct_fmt"],
            "z": al["z_fmt"],
            "Expected outcome": icon_map.get(a["route"], a["route"]),
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    st.divider()
    for i, a in enumerate(ALERTS):
        al = a["alert"]
        c1, c2 = st.columns([4, 1])
        c1.markdown(
            f"**{al['id']} · {al['kpi']} — {al['category']} / "
            f"{al['region']}**  \n"
            f"Current {al['current_fmt']} vs baseline {al['baseline_fmt']} "
            f"→ **{al['pct_fmt']}** ({al['delta_fmt']}, z={al['z_fmt']})")
        c2.button("Analyze →", key=f"open_{al['id']}",
                  width="stretch", on_click=open_alert, args=(i,))
    st.stop()

# ========================================================== DETAIL VIEW ====
A = ALERTS[ss["alert_idx"]]
a = A["alert"]
aid = a["id"]
route = A["route"]
order = ORDER[route]
cur_step_num = order[min(ss["step_pos"], len(order) - 1)]

top1, top2 = st.columns([1, 1])
top1.button("← Back to Alerts", on_click=lambda: ss.update(view="list"))
top2.button("↻ Restart this analysis", on_click=open_alert,
            args=(ss["alert_idx"],))

st.title(f"{aid} — {a['kpi']} · {a['category']} / {a['region']}")
prog = (ss["step_pos"] + 1) / len(order)
st.progress(prog, text=f"Pipeline progress — step {cur_step_num} of "
                       f"{order[-1]} ({route.replace('_', ' ').title()})")

# ------------------------------------------------------------ step blocks --
def step_header(n):
    st.caption(f"STEP {n}")


def render_step_1():
    with st.container(border=True):
        step_header(1)
        st.subheader("Alert Summary")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(f"{a['kpi']} — week {a['week_start']}", a["current_fmt"],
                  a["pct_fmt"])
        m2.metric("Baseline (trailing 4 wk)", a["baseline_fmt"])
        m3.metric("Δ business impact", a["delta_fmt"])
        m4.metric("z-score vs baseline", a["z_fmt"])
        st.info(
            f"**Why flagged material:** |z| = {abs(a['z_score']):.2f} ≥ 1.5 "
            f"AND |Δ| = {abs(a['pct_change']) * 100:.1f}% ≥ 10%."
            if not a["low_data"] else
            "**Why flagged:** insufficient baseline history — surfaced for "
            "review rather than silently dropped.")
        st.caption(f"Baseline weeks available: {a['baseline_weeks']}. "
                   f"Ranked #{ss['alert_idx'] + 1} of {len(ALERTS)} by "
                   f"absolute rupee impact.")


def render_step_2():
    with st.container(border=True):
        animate((aid, 2),
                "Resampling daily sales data to weekly grain to align with "
                "campaign data...", 0.9)
        step_header(2)
        st.subheader("Reconciliation")
        for line in A["reconcile_log"]:
            st.write(f"• {line}")
        st.caption("Grain mismatch between sources is real: sales and "
                   "inventory are daily, campaigns are weekly. Comparisons "
                   "happen only after alignment — logged, not hidden.")


def render_step_3():
    with st.container(border=True):
        animate((aid, 3), "Scanning Change Log...", 0.9)
        step_header(3)
        st.subheader("Fast Path Check")
        fp = A["fast_path"]
        if fp:
            st.success(f"**Direct match found** — logged event on "
                       f"{fp['event_date']}: *{fp['description']}* "
                       f"(type: `{fp['event_type']}`, window {fp['window']})."
                       "\n\nSkipping deep hypothesis testing — cheap, fast, "
                       "explainable. Confidence fixed at High.")
        else:
            st.warning("**No direct match in Change Log** within ±2 days of "
                       "this alert window — escalating to Deep Path: "
                       "competing hypotheses will be tested and falsified.")


def render_step_4():
    with st.container(border=True):
        animate((aid, 4), "Generating candidate hypotheses...", 0.6)
        step_header(4)
        st.subheader("Hypothesis Testing — tested & falsified against data")
        hyp_names = ["supply-side", "demand-side", "pricing"]
        for h, nm in zip(A["hypotheses"], hyp_names):
            animate((aid, "hyp", nm), f"Testing {nm} hypothesis against "
                    f"data...", 0.9)
            ok = h["supported"]
            tag = ":green-badge[SUPPORTED]" if ok else ":red-badge[REJECTED]"
            st.markdown(f"**{h['name']}** {tag}")
            st.write(h["verdict"])
            st.caption(f"Deciding metric: {h['deciding_metric']} → "
                       f"**{h['deciding_value']}**  ·  Source: "
                       f"{h['data_source']}")
            st.divider()
        st.caption("Rejected hypotheses stay visible on purpose — you just "
                   "watched the system consider them and kill each one with "
                   "an actual number.")


def render_step_5():
    with st.container(border=True):
        animate((aid, 5), "Scoring confidence...", 0.9)
        step_header(5)
        st.subheader("Confidence Score")
        c = A["confidence"]
        tier_color = {"High": "green", "Medium": "orange", "Low": "red"}[
            c["tier"]]
        st.markdown(f"#### {c['score']:.2f} :{tier_color}-badge[{c['tier']}]"
                    f" confidence")
        cc1, cc2 = st.columns(2)
        items = list(c["components"].items())
        for i, (k, v) in enumerate(items):
            (cc1 if i < 2 else cc2).write(f"{k.replace('_', ' ')}: `{v}`")
        st.progress(min(max(c["score"], 0.0), 1.0))
        st.caption("Weighted: temporal .30 · source agreement .25 · "
                   "completeness .25 · hypothesis margin .20")


def halt_abstain():
    st.error("🛑 **PIPELINE HALTED — INSUFFICIENT EVIDENCE. The LLM was NOT "
             "called.**\n\n" + A["abstention"]["message"] +
             "\n\nThe system refuses to generate an explanation it cannot "
             "support. This abstention is earned from the data, not scripted.")


def render_step_6():
    with st.container(border=True):
        animate((aid, 6),
                "Cross-checking against comparable regions/products...",
                0.9)
        step_header(6)
        st.subheader("Conflict Check")
        cf = A["conflict"]
        if cf["conflict"]:
            st.warning("**CONTRADICTION DETECTED**\n\n"
                       f"- Signal A: {cf['signal_a']}\n"
                       f"- Signal B: {cf['signal_b']}")
            st.error("🛑 **PIPELINE HALTED — FLAGGED FOR MANUAL REVIEW. No "
                     "LLM narrative was generated.**\n\nWhen the data "
                     "disagrees with itself, CAUSE does not silently pick a "
                     "winner — it stops and escalates.")
        else:
            st.success("No conflicts found.")
            note = cf.get("note")
            cells = cf.get("comparable_cells") or []
            if note:
                st.write(note)
            if cells:
                st.caption("Comparable exposure checked: " +
                           json.dumps(cells))


def render_persona_and_gate():
    with st.container(border=True):
        new_persona = st.radio("Persona", ["Category Manager", "CXO"],
                               key="persona",
                               horizontal=True,
                               help="CXO sees category aggregates only; SKU "
                                    "fields are redacted by a deterministic "
                                    "access gate.")
        step_header(7)
        st.subheader("Access Gate")
        if new_persona == "CXO":
            redact_for_cxo({"x": 1})   # ensures log line exists
            st.write("🔒 Access check: **CXO** role → SKU/product-level "
                     "fields redacted; category aggregates only.")
        else:
            st.write("🔓 Access check: **Category Manager** role → full "
                     "SKU-level detail allowed.")


def build_payload():
    return redact_for_cxo(dict(A)) if ss["persona"] == "CXO" else dict(A)


def render_step_8():
    with st.container(border=True):
        animate((aid, 8), "Generating explanation...", 0.9)
        step_header(8)
        st.subheader(f"Narration — {ss['persona']}")
        key = (aid, ss["persona"])
        if key not in ss["narrations"]:
            payload = build_payload()
            t0 = time.perf_counter()
            text, engine_lbl = llm.narrate(payload, ss["persona"])
            clean, removed, audit_engine = llm.self_verify(text, payload)
            ms = round((time.perf_counter() - t0) * 1000, 1)
            ss["narrations"][key] = {
                "raw": text, "clean": clean, "removed": removed,
                "engine": engine_lbl, "audit_engine": audit_engine, "ms": ms}
        N = ss["narrations"][key]
        st.caption(f"Generated by: {N['engine']} · input to the model = "
                   "finished JSON only (no raw rows)")
        st.markdown(N["clean"])
        with st.expander("Exact JSON handed to the LLM (after access gate)"):
            safe = json.loads(json.dumps(build_payload(), default=str))
            st.json({k: v for k, v in safe.items() if k != "fast_path"})


def render_step_9():
    with st.container(border=True):
        animate((aid, 9), "Checking narrative against evidence...", 0.9)
        step_header(9)
        st.subheader("Self-Verification")
        N = ss["narrations"].get((aid, ss["persona"]))
        if N is None:   # persona switched after step 8; regenerate quietly
            payload = build_payload()
            text, engine_lbl = llm.narrate(payload, ss["persona"])
            clean, removed, audit_engine = llm.self_verify(text, payload)
            N = {"raw": text, "clean": clean, "removed": removed,
                 "engine": engine_lbl, "audit_engine": audit_engine,
                 "ms": 0.0}
            ss["narrations"][(aid, ss["persona"])] = N
        if N["removed"]:
            for r in N["removed"]:
                claim = r.get("claim_sentence") or r.get("claim", "")
                st.warning("⚠️ Unverified claim detected and removed: "
                           + claim)
            st.markdown(N["clean"])
        else:
            st.success("✅ All claims verified against evidence — every "
                       "number in the narrative traces to a field in the "
                       "source JSON.")
        st.caption(f"Audited by: {N['audit_engine']}")


def render_step_10():
    with st.container(border=True):
        animate((aid, 10), None, 0)
        step_header(10)
        st.subheader("Recommendation")
        rec = A["recommendation"]
        st.write(f"**{rec['action']}**")
        if rec.get("est_impact_fmt"):
            st.write(f"Estimated impact: **{rec['est_impact_fmt']} / week** "
                     f"— basis: {rec['basis']}")
        else:
            st.caption(f"Basis: {rec['basis']}")
        st.divider()
        st.markdown("**Analyst decision** — logged to `decisions.csv`; "
                    "feeds back into confidence weighting over time.")
        b1, b2, b3 = st.columns(3)
        clicked = None
        if b1.button("👍 Approve", key=f"ap_{aid}", width="stretch"):
            clicked = "approve"
        if b2.button("👎 Dismiss", key=f"dis_{aid}", width="stretch"):
            clicked = "dismiss"
        if b3.button("🔎 Request more evidence", key=f"req_{aid}",
                     width="stretch"):
            clicked = "request_more_evidence"
        if clicked:
            pd.DataFrame([{"alert_id": aid, "category": a["category"],
                           "region": a["region"], "route": route,
                           "decision": clicked}]).to_csv(
                Path("cause/data/decisions.csv"), mode="a",
                header=not Path("cause/data/decisions.csv").exists(),
                index=False)
            st.toast(f"Logged '{clicked}' for {aid}", icon="📝")


RENDERERS = {1: render_step_1, 2: render_step_2, 3: render_step_3,
             4: render_step_4, 5: render_step_5, 6: render_step_6,
             10: render_step_10}

for pos, n in enumerate(order[:ss["step_pos"] + 1]):
    if n == 7:
        render_persona_and_gate()
    elif n == 8:
        render_step_8()
    elif n == 9:
        render_step_9()
    else:
        RENDERERS[n]()

    if n == 5 and route == "ABSTAIN":
        halt_abstain()

# --------------------------------------------------------- next / advance --
halted = (route == "ABSTAIN" and cur_step_num == 5) or \
         (route == "UNRESOLVED_CONFLICT" and cur_step_num == 6)

if not halted and ss["step_pos"] < len(order) - 1:
    nxt = order[ss["step_pos"] + 1]
    label = NEXT_LABEL[cur_step_num]
    if cur_step_num == 3 and A["fast_path"]:
        label = "Run Conflict Check →"
    st.divider()
    _, mid, _ = st.columns([1, 2, 1])
    mid.button(label, key=f"next_{aid}_{ss['step_pos']}",
               width="stretch",
               on_click=lambda: ss.update(step_pos=ss["step_pos"] + 1))

# ------------------------------------------------------- evidence ledger ---
with st.container():
    st.divider()
    st.subheader("Evidence Ledger")
    st.caption("Which steps were deterministic vs LLM, with latency. "
               "Populates as the pipeline advances.")
    completed = set(order[:ss["step_pos"] + 1])
    rows = []
    occ = {}
    for r in P["ledger_rows"]:
        base = r["step"].split("[")[0].strip()
        occ[r["step"]] = occ.get(r["step"], 0) + 1
        # include global rows once, per-alert rows only for this alert
        is_this_alert = "[" in r["step"] and f"[{aid}]" in r["step"]
        is_global = "[" not in r["step"]
        if not (is_global or is_this_alert):
            continue
        step_no = int(base.split()[1])
        if base.startswith("Step 1") and 1 in completed:
            shown = True
        elif base.startswith("Step 2") and 2 in completed:
            shown = True
        else:
            shown = step_no in completed
        if not shown:
            continue
        eng = "LLM call" if r["engine"] == "LLM call" else "Deterministic"
        rows.append({"step": r["step"], "engine": eng,
                     "latency_ms": r["latency_ms"],
                     "est_cost_usd": r["est_cost_usd"], "note": r["note"]})
    N = ss["narrations"].get((aid, ss["persona"]))
    if N and 8 in completed:
        rows.append({"step": f"Step 8 Narration [{aid}]",
                     "engine": N["engine"],
                     "latency_ms": N.get("ms"),
                     "est_cost_usd": None,
                     "note": f"persona={ss['persona']}"})
    if N and 9 in completed:
        rows.append({"step": f"Step 9 Self-Verify [{aid}]",
                     "engine": N["audit_engine"],
                     "latency_ms": None, "est_cost_usd": None,
                     "note": f"{len(N['removed'])} claim(s) removed"})
    det = sum(1 for r in rows if r["engine"].startswith("Deterministic"))
    lm = sum(1 for r in rows if r["engine"] == "LLM call")
    m1, m2 = st.columns(2)
    m1.metric("Deterministic steps shown", det)
    m2.metric("LLM steps shown", lm)
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
