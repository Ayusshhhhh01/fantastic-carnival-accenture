"""
CAUSE — premium enterprise redesign (Accenture violet design system).
Login -> persona-scoped dashboard -> modal diagnosis flow.
Pure styling/UX per design addendum; engine + LLM logic unchanged.
"""
import json
import time
from pathlib import Path

import pandas as pd
import streamlit as st

from cause.engine import run, redact_for_cxo, fmt_inr, FACTOR_LABELS
from cause import llm

try:
    import altair as alt
except ImportError:
    alt = None

st.set_page_config(page_title="CAUSE", page_icon="◈", layout="wide")

# ------------------------------------------------------------- palette ----
VIOLET = "#A100FF"
INK = "#1A1A1A"
BODY = "#3A3A45"
META = "#6B6B78"
LINE = "#E5E5EA"
CARD = "#FFFFFF"
BG = "#F7F7FA"
TINT = "#F3E8FF"                      # pale violet highlight
GOOD, GOOD_BG = "#2E7D5B", "#E6F4EC"
MEDI, MEDI_BG = "#6B7280", "#EEF0F3"
LOW, LOW_BG = "#B8860B", "#FBF3DC"
CONF, CONF_BG = "#C0392B", "#FBEAE8"

st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stButton button {{
  font-family: 'Inter', -apple-system, 'Segoe UI', Roboto, sans-serif;
}}
.block-container {{padding-top: 2rem; padding-bottom: 3rem; max-width: 1180px;}}
h1 {{font-size: 23px !important; font-weight: 700 !important; color: {INK};}}
h2 {{font-size: 19px !important; font-weight: 650 !important; color: {INK};}}
h3 {{font-size: 16px !important; font-weight: 600 !important; color: {INK};}}
p, li {{font-size: 14px; color: {BODY}; line-height: 1.55;}}
[data-testid="stCaption"], [data-testid="stMarkdownContainer"] caption {{
  color: {META}; font-size: 12px;
}}
/* cards */
[data-testid="stVerticalBlockBorderWrapper"] {{
  background: {CARD}; border: 1px solid {LINE} !important;
  border-radius: 14px !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04);
  transition: transform .15s ease, box-shadow .15s ease;
}}
[data-testid="stVerticalBlockBorderWrapper"]:hover {{
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.10), 0 2px 4px rgba(0,0,0,0.05);
}}
/* buttons */
.stButton > button {{
  border-radius: 8px; font-weight: 600; font-size: 13.5px;
  padding: 6px 14px;
}}
.stButton > button[kind="primary"] {{
  background: {VIOLET} !important; color: #FFFFFF !important;
  border: none !important;
}}
.stButton > button[kind="primary"]:hover {{
  background: #8900D6 !important;
}}
.stButton > button[kind="secondary"] {{
  background: {CARD} !important; color: {BODY} !important;
  border: 1px solid {LINE} !important;
}}
.stButton > button[kind="secondary"]:hover {{
  border-color: {VIOLET} !important; color: {VIOLET} !important;
}}
/* progress = confidence bar */
[data-testid="stProgress"] > div {{
  background: #ECECF1 !important; border-radius: 99px;
}}
[data-testid="stProgress"] > div > div {{
  background: {VIOLET} !important; border-radius: 99px;
}}
/* dialogs float */
div[data-testid="stDialog"] div[role="dialog"] {{
  border-radius: 16px;
  box-shadow: 0 24px 60px rgba(0,0,0,0.25);
}}
div[data-testid="stDialog"] div[role="dialog"]::before {{
  content: ''; position: fixed; inset: 0; background: rgba(20,10,35,0.45);
}}
hr {{border-color: {LINE}; margin: 1.2rem 0;}}
</style>""", unsafe_allow_html=True)

ss = st.session_state
for k, v in {
    "pipeline": None, "current_persona": None, "open_aid": None,
    "stage": "detail", "sel": 0, "played": set(), "handled": {},
    "narrations": {}, "flash": None,
}.items():
    ss.setdefault(k, v)
if ss["pipeline"] is None:
    ss["pipeline"] = run()
P = ss["pipeline"]
ALERTS = P["alerts"]

PERSONAS = {
    "cm_elex": {"name": "Category Manager", "scope": "Electronics",
                "short": "CM · Electronics", "mono": "CM",
                "cats": ["Electronics"], "llm_persona": "Category Manager"},
    "cm_home": {"name": "Category Manager", "scope": "Apparel & Home",
                "short": "CM · Apparel & Home", "mono": "CM",
                "cats": ["Apparel", "Home & Kitchen"],
                "llm_persona": "Category Manager"},
    "cxo": {"name": "CXO", "scope": "All categories",
            "short": "CXO", "mono": "CXO", "cats": None, "top_n": 3,
            "llm_persona": "CXO"},
}

ROUTE_LABEL = {"RESOLVED": "Diagnosed", "FAST_PATH": "Direct match",
               "UNRESOLVED_CONFLICT": "Conflict", "ABSTAIN": "Low evidence"}


def pill(text, fg, bg):
    return (f"<span style='background:{bg};color:{fg};padding:3px 11px;"
            f"border-radius:99px;font-size:11px;font-weight:600;"
            f"letter-spacing:.02em;'>{text}</span>")


def tier_pill(p):
    if p >= 75:
        return pill("HIGH CONFIDENCE", GOOD, GOOD_BG), GOOD
    if p >= 50:
        return pill("MEDIUM CONFIDENCE", MEDI, MEDI_BG), MEDI
    return pill("LOW CONFIDENCE", LOW, LOW_BG), LOW


def severity_hex(a):
    if a["route"] == "UNRESOLVED_CONFLICT":
        return CONF
    if a["route"] == "ABSTAIN":
        return LOW
    return CONF if abs(a["alert"]["delta_inr"]) >= 25e5 else \
        (LOW if abs(a["alert"]["delta_inr"]) >= 10e5 else GOOD)


def route_pill(route):
    m = {"RESOLVED": (GOOD, GOOD_BG), "FAST_PATH": (GOOD, GOOD_BG),
         "UNRESOLVED_CONFLICT": (CONF, CONF_BG), "ABSTAIN": (LOW, LOW_BG)}
    fg, bg = m.get(route, (MEDI, MEDI_BG))
    return pill(ROUTE_LABEL[route], fg, bg)


def alerts_for(pid):
    p = PERSONAS[pid]
    if p["cats"] is None:
        top = sorted(ALERTS, key=lambda x: -abs(x["alert"]["delta_inr"]))
        return top[:p["top_n"]]
    return [a for a in ALERTS if a["alert"]["category"] in p["cats"]]


def ranked_hyps(A):
    return sorted(A["hypotheses"], key=lambda h: h["confidence_pct"],
                  reverse=True)


# ------------------------------------------------------------- snapshots --
@st.cache_data
def _frames():
    d = Path("cause/data")
    s = pd.read_csv(d / "sales_daily.csv", parse_dates=["date"])
    c = pd.read_csv(d / "campaigns_weekly.csv", parse_dates=["week_start"])
    return s, c


def _axis_dark(chart):
    return chart.configure_view(stroke=None).configure_axis(
        gridColor=LINE, labelColor=META, titleColor=META, domain=False)


def snapshot_alert_chart(A, height=200):
    a = A["alert"]
    if a["kpi"] == "Marketing Spend":
        _, c = _frames()
        w = c[c.category.eq(a["category"])].groupby(
            "week_start", as_index=False)["spend"].sum() \
            .sort_values("week_start").tail(8) \
            .rename(columns={"week_start": "week", "spend": "value"})
    else:
        s, _ = _frames()
        m = s.category.eq(a["category"])
        if a["region"] != "(all)":
            m &= s.region.eq(a["region"])
        d = s[m].copy()
        d["week"] = d["date"] - pd.to_timedelta(d["date"].dt.dayofweek,
                                                unit="D")
        w = d.groupby("week", as_index=False)["revenue"].sum() \
             .sort_values("week").tail(8).rename(columns={"revenue": "value"})
    hl = pd.Timestamp(a["week_start"])
    ytitle = "Spend / wk" if a["kpi"] == "Marketing Spend" else "Revenue / wk"
    band = alt.Chart(pd.DataFrame({"s": [hl], "e": [hl + pd.Timedelta(days=7)]})) \
        .mark_rect(color="#C0392B18").encode(x="s:T", x2="e:T")
    line = alt.Chart(w).mark_line(color=VIOLET, point={"color": VIOLET}) \
        .encode(x=alt.X("week:T", title=None),
                y=alt.Y("value:Q", title=ytitle,
                        axis=alt.Axis(format="~s")))
    st.altair_chart(_axis_dark(band + line).properties(height=height),
                    width="stretch")


def snapshot_hyp_chart(A, h, height=140):
    a = A["alert"]
    d = h.get("detail") or {}
    s, c = _frames()

    if h["name"].startswith("Supply") and d.get("product_id"):
        dd = s[(s.product_id == d["product_id"]) &
               (s.region == a["region"])].sort_values("date").tail(14)
        so = set(map(pd.Timestamp, d.get("stockout_days", [])))
        dd = dd.assign(state=dd.date.map(
            lambda x: "Stock-out" if x in so else "Normal"))
        ch = alt.Chart(dd).mark_bar().encode(
            x=alt.X("date:T", title=None, axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("revenue:Q", title=None, axis=alt.Axis(format="~s")),
            color=alt.Color("state:N", scale=alt.Scale(
                domain=["Normal", "Stock-out"],
                range=["#DDDDE6", CONF]), legend=None))
        st.altair_chart(_axis_dark(ch).properties(height=height),
                        width="stretch")

    elif h["name"].startswith("Demand"):
        cc = c[c.category.eq(a["category"])]
        if a["region"] != "(all)":
            cc = cc[cc.region.eq(a["region"])]
        w = cc.groupby("week_start", as_index=False)["spend"].sum() \
              .sort_values("week_start").tail(8)
        w["flag"] = ["This week" if x == pd.Timestamp(a["week_start"])
                     else "Prior" for x in w.week_start]
        ch = alt.Chart(w).mark_bar().encode(
            x=alt.X("week_start:T", title=None,
                    axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("spend:Q", title=None, axis=alt.Axis(format="~s")),
            color=alt.Color("flag:N", scale=alt.Scale(
                domain=["Prior", "This week"],
                range=["#DDDDE6", VIOLET]), legend=None))
        st.altair_chart(_axis_dark(ch).properties(height=height),
                        width="stretch")

    elif h["name"].startswith("Pricing"):
        m = s.category.eq(a["category"])
        if a["region"] != "(all)":
            m &= s.region.eq(a["region"])
        dd = s[m].groupby("date", as_index=False)["unit_price"].mean() \
                 .sort_values("date").tail(21)
        ch = alt.Chart(dd).mark_line(color=VIOLET).encode(
            x=alt.X("date:T", title=None, axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("unit_price:Q", title=None,
                    axis=alt.Axis(format="~s")))
        st.altair_chart(_axis_dark(ch).properties(height=height),
                        width="stretch")
    else:
        snapshot_alert_chart(A, height=height)


def conf_bar(pct):
    c1, c2 = st.columns([3, 1])
    c1.progress(min(pct, 100) / 100.0)
    c2.markdown(f"<span style='font-size:13px;font-weight:700;color:"
                f"{tier_pill(pct)[1]}'>{pct}%</span>",
                unsafe_allow_html=True)


def flash_toast():
    if ss.get("flash"):
        st.toast(ss.pop("flash"), icon="✅")


# =========================================================== LOGIN SCREEN ==
if ss["current_persona"] is None:
    _, mid, _ = st.columns([1.3, 1.5, 1.3])
    with mid:
        st.write("")
        st.markdown(
            f"<h1 style='text-align:center;font-size:34px;margin-bottom:2px;'>"
            f"<span style='color:{VIOLET}'>&#9679;</span> CAUSE</h1>",
            unsafe_allow_html=True)
        st.markdown(f"<p style='text-align:center;color:{META};margin-top:0;"
                    f"font-size:14px;'>Every alert explained. Every number "
                    f"verified. Nothing taken on faith.</p>",
                    unsafe_allow_html=True)
        st.write("")
        cols = st.columns(3)
        for col, (pid, p) in zip(cols, PERSONAS.items()):
            with col, st.container(border=True):
                st.markdown(
                    f"<div style='text-align:center;padding:18px 4px 8px;'>"
                    f"<div style='width:52px;height:52px;border-radius:50%;"
                    f"background:{TINT};color:{VIOLET};font-weight:700;"
                    f"display:inline-flex;align-items:center;"
                    f"justify-content:center;font-size:17px;'>{p['mono']}"
                    f"</div>"
                    f"<div style='font-weight:600;margin-top:12px;"
                    f"font-size:14px;color:{INK};'>{p['name']}</div>"
                    f"<div style='color:{META};font-size:12px;margin-top:2px;"
                    f"'>{p['scope']}</div></div>", unsafe_allow_html=True)
                if st.button("Enter", key=f"login_{pid}", width="stretch"):
                    ss["current_persona"] = pid
                    ss["flash"] = None
                    st.rerun()
        st.write("")
        st.caption("Deterministic analysis engine · audited LLM narration · "
                   "synthetic retail data")
    st.stop()

# ============================================================= DASHBOARD ==
persona = PERSONAS[ss["current_persona"]]
flash_toast()
my_alerts = alerts_for(ss["current_persona"])

hd1, hd2 = st.columns([4, 1])
with hd1:
    st.markdown(f"<span style='color:{VIOLET};font-size:15px;'>&#9679;</span> "
                f"<span style='font-weight:700;font-size:15px;color:{INK};'>"
                f"CAUSE</span> <span style='color:{META};font-size:12.5px;'>"
                f"&nbsp;{persona['short']}</span>", unsafe_allow_html=True)
    n = len([a for a in my_alerts if a["alert"]["id"] not in ss["handled"]])
    scope_txt = ("highest ₹ impact across all categories"
                 if ss["current_persona"] == "cxo" else
                 "in " + " & ".join(persona["cats"]))
    if n:
        st.markdown(f"<h1 style='margin-bottom:0'>{n} alert"
                    f"{'s' if n != 1 else ''} need"
                    f"{'s' if n == 1 else ''} your attention</h1>",
                    unsafe_allow_html=True)
        st.caption(f"Week of {P['cur_week']} · ranked by ₹ impact · {scope_txt}")
    else:
        st.markdown("<h1>All clear</h1>", unsafe_allow_html=True)
        st.caption(f"Week of {P['cur_week']} — nothing left in your scope.")
with hd2:
    st.write("")
    st.button("Switch persona", width="stretch",
              on_click=lambda: ss.update(current_persona=None))

active = [a for a in my_alerts if a["alert"]["id"] not in ss["handled"]]
handled_ids = [a["alert"]["id"] for a in my_alerts
               if a["alert"]["id"] in ss["handled"]]

if active:
    nrows = -(-len(active) // 3)
    rows = [st.columns(3) for _ in range(nrows)]
    for i, A in enumerate(active):
        al = A["alert"]
        col = rows[i // 3][i % 3]
        pct = al["pct_change"]
        pct_txt = "new" if pct is None else f"{pct * 100:+.1f}%"
        sev = severity_hex(A)
        with col, st.container(border=True, height=215):
            st.markdown(route_pill(A["route"]), unsafe_allow_html=True)
            st.write("")
            st.markdown(f"<span style='font-size:14.5px;font-weight:600;"
                        f"color:{INK};'>{al['kpi']} · {al['category']}</span>"
                        + (f"<span style='color:{META};font-size:12px;'>&nbsp;"
                           f"{al['region'].replace('Region ', '')}</span>"
                           if al["region"] != "(all)" else ""),
                        unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.markdown(f"<span style='font-size:24px;font-weight:750;"
                        f"color:{sev}'>{pct_txt}</span><br><span style="
                        f"'color:{META};font-size:11.5px;'>vs 4-wk baseline"
                        f"</span>", unsafe_allow_html=True)
            c2.markdown(f"<span style='font-size:17px;font-weight:650;"
                        f"color:{INK};'>{al['delta_fmt']}</span><br><span "
                        f"style='color:{META};font-size:11.5px;'>impact</span>",
                        unsafe_allow_html=True)
            st.button("Investigate", key=f"card_{al['id']}",
                      width="stretch", type="primary",
                      on_click=lambda aid=al["id"]: ss.update(
                          open_aid=aid, stage="detail", sel=0))

if handled_ids:
    st.divider()
    chips = " ".join(
        f"<span style='background:#FFFFFF;border:1px solid {LINE};"
        f"color:{META};padding:3px 11px;border-radius:99px;font-size:11.5px;"
        f"'>{i} · {ss['handled'][i]['decision']}</span>" for i in handled_ids)
    st.markdown(f"<span style='color:{META};font-size:12px;'>Recently "
                f"handled</span> &nbsp;" + chips, unsafe_allow_html=True)


# ====================================================== MODAL STATE MACHINE
def make_ignorer(aid):
    def go():
        ss["handled"][aid] = {"decision": "ignored", "feedback": ""}
        ss["open_aid"] = None
        ss["flash"] = "Alert ignored — removed from your queue"
    return go


def make_decider(aid, al, route, decision):
    def go():
        reason = ss.get(f"fb_{aid}", "") or ""
        if reason == "Other":
            reason = ss.get(f"fbo_{aid}", "") or "Other"
        ss["handled"][aid] = {"decision": decision, "feedback": reason}
        ss["open_aid"] = None
        ss["flash"] = ("Recommendation approved ✓" if decision == "approved"
                       else "Recommendation rejected")
        pd.DataFrame([{"alert_id": aid, "category": al["category"],
                       "region": al["region"], "route": route,
                       "persona": persona["short"], "decision": decision,
                       "feedback": reason}]).to_csv(
            Path("cause/data/decisions.csv"), mode="a",
            header=not Path("cause/data/decisions.csv").exists(), index=False)
    return go


@st.dialog("Root Cause Analysis", width="large")
def rca_modal():
    A = next(x for x in ALERTS if x["alert"]["id"] == ss["open_aid"])
    al = A["alert"]
    route = A["route"]
    hyps = ranked_hyps(A)

    def close():
        ss["open_aid"] = None
        st.rerun()

    def header_line():
        direction = "down" if al["delta_inr"] < 0 else "up"
        if al["pct_change"] is None:
            st.subheader(f"{al['kpi']} — {al['category']} — new signal, no "
                         f"baseline")
        else:
            st.subheader(f"{al['kpi']} — {al['category']}"
                         + (f" — {al['region']}" if al["region"] != "(all)"
                            else "")
                         + f" — {direction} "
                           f"{abs(al['pct_change']) * 100:.1f}%")
        st.caption(f"Impact {al['delta_fmt']} · z={al['z_fmt']} · week "
                   f"{al['week_start']}")

    # ---------- Modal 1 : detail ----------
    if ss["stage"] == "detail":
        header_line()
        snapshot_alert_chart(A, height=200)
        st.caption("Weekly KPI trend · shaded band marks the week that "
                   "breached the materiality rule (|z| ≥ 1.5 and |Δ| ≥ 10%)")
        b1, b2, _ = st.columns([1, 1, 2])
        b1.button("Diagnose", type="primary", width="stretch",
                  key=f"d_{al['id']}",
                  on_click=lambda: ss.update(stage="diagnosing"))
        b2.button("Ignore", width="stretch", key=f"ig_{al['id']}",
                  help="Removes this alert from your queue",
                  on_click=make_ignorer(al["id"]))

    # ---------- diagnosing loader ----------
    elif ss["stage"] == "diagnosing":
        key = ("diag", al["id"])
        if key not in ss["played"]:
            fp = A["fast_path"]
            steps = [("Scanning ops Change Log…",
                      "direct match found" if fp else
                      "no match — escalating to deep path")]
            if not fp:
                for h in hyps:
                    steps.append((f"Testing {h['name']}…",
                                  f"{h['confidence_pct']}% · "
                                  f"{'supported' if h['supported'] else 'rejected'}"))
                steps.append(("Scoring confidence with per-candidate "
                              "weights…", "done"))
            st.subheader("Diagnosing…")
            bar = st.progress(0.0, text="Starting engine…")
            lines = [st.empty() for _ in steps]
            for i, (txt, done) in enumerate(steps):
                lines[i].markdown(f"<span style='color:{LOW};'>◌</span> "
                                  f"<span style='color:{BODY};'>{txt}</span>",
                                  unsafe_allow_html=True)
                time.sleep(0.85)
                lines[i].markdown(f"<span style='color:{GOOD};'>✓</span> "
                                  f"<span style='color:{BODY};'>{txt}</span> "
                                  f"<span style='color:{META};'>— {done}"
                                  f"</span>", unsafe_allow_html=True)
                bar.progress((i + 1) / len(steps),
                             text=f"Step {i + 1} of {len(steps)}")
            time.sleep(0.5)
            ss["played"].add(key)
            if fp:
                ss.update(stage="recommendation", sel=None)
            elif route == "ABSTAIN":
                ss["stage"] = "abstain"
            else:
                ss.update(stage="rca_list", sel=0)
            st.rerun()

    # ---------- amber dead-end ----------
    elif ss["stage"] == "abstain":
        header_line()
        with st.container(border=True):
            st.markdown(pill("INSUFFICIENT EVIDENCE", LOW, LOW_BG),
                        unsafe_allow_html=True)
            st.write("")
            st.warning(A["abstention"]["message"])
            st.caption("The pipeline stopped here by design — CAUSE will not "
                       "generate an explanation the data cannot support. No "
                       "LLM was called.")
        st.write("")
        if st.button("← Back to Dashboard", type="primary",
                     width="stretch"):
            close()

    # ---------- Modal 2 : RCA list ----------
    elif ss["stage"] == "rca_list":
        header_line()
        st.caption("Candidates revealed as their tests complete · Confidence "
                   "= W₁·Temporal + W₂·Source Reliability + W₃·Contrary "
                   "Stats + W₄·Evidence Density, weighted per candidate type")
        first = ("rca", al["id"]) not in ss["played"]
        for i, h in enumerate(hyps):
            tp, tcol = tier_pill(h["confidence_pct"])
            with st.container(border=True):
                c1, c2, c3 = st.columns([4.6, 2, 1.1])
                badge = pill("SUPPORTED", GOOD, GOOD_BG) if h["supported"] \
                    else pill("REJECTED", CONF, CONF_BG)
                one_liner = h["verdict"].split(" - ")[0]
                c1.markdown(f"**{i + 1}. {h['name']}**&nbsp;&nbsp;{badge}",
                            unsafe_allow_html=True)
                c1.caption(one_liner)
                with c2:
                    conf_bar(h["confidence_pct"])
                c3.markdown(tp, unsafe_allow_html=True)
                c3.button("Expand", key=f"ex_{al['id']}_{i}",
                          width="stretch",
                          on_click=lambda i=i: ss.update(stage="rca_expand",
                                                         sel=i))
            if first:
                time.sleep(0.45)
        if first:
            ss["played"].add(("rca", al["id"]))
        st.divider()
        _, mid, _ = st.columns([1, 2, 1])
        mid.button("Continue →", type="primary", width="stretch",
                   key=f"cont_{al['id']}",
                   on_click=lambda: ss.update(sel=0,
                                              stage="recommendation"))

    # ---------- Modal 3 : expand ----------
    elif ss["stage"] == "rca_expand":
        h = hyps[ss["sel"]]
        winner_idx = next((i for i, x in enumerate(hyps)
                           if x["supported"]), 0)
        tp, _ = tier_pill(h["confidence_pct"])
        header_line()
        st.markdown(f"Candidate {ss['sel'] + 1}/{len(hyps)} &nbsp;"
                    + (pill("SUPPORTED", GOOD, GOOD_BG) if h["supported"]
                       else pill("REJECTED", CONF, CONF_BG))
                    + f" &nbsp;{tp}", unsafe_allow_html=True)
        row1 = st.columns(2)
        with row1[0], st.container(border=True, height=240):
            st.markdown(f"<span style='font-size:12px;font-weight:600;"
                        f"color:{VIOLET};letter-spacing:.04em;'>VERDICT"
                        f"</span>", unsafe_allow_html=True)
            st.write(h["verdict"])
            st.caption("Source: " + h["data_source"])
        with row1[1], st.container(border=True, height=240):
            st.markdown(f"<span style='font-size:12px;font-weight:600;"
                        f"color:{VIOLET};letter-spacing:.04em;'>DATA "
                        f"SNAPSHOT</span>", unsafe_allow_html=True)
            snapshot_hyp_chart(A, h, height=145)
        row2 = st.columns(2)
        with row2[0], st.container(border=True, height=225):
            st.markdown(f"<span style='font-size:12px;font-weight:600;"
                        f"color:{VIOLET};letter-spacing:.04em;'>HOW THE "
                        f"SCORE WAS CALCULATED</span>", unsafe_allow_html=True)
            w = h["weights"]; f = h["factors"]
            for k in ("temporal_correlation", "source_agreement",
                      "hypothesis_margin", "data_completeness"):
                sym, lbl = FACTOR_LABELS[k]
                fv = round(f[k] * 100)
                st.markdown(
                    f"<span style='color:{META};font-size:12.5px;'>{sym} "
                    f"{w[k]:.2f} × {lbl}</span>"
                    f"<span style='float:right;color:{INK};font-size:12.5px;"
                    f"font-weight:600;'>&nbsp;&nbsp;{fv}% × {w[k]:.2f}"
                    f"</span>", unsafe_allow_html=True)
            st.write("")
            conf_bar(h["confidence_pct"])
        with row2[1], st.container(border=True, height=225):
            st.markdown(f"<span style='font-size:12px;font-weight:600;"
                        f"color:{VIOLET};letter-spacing:.04em;'>CONTRADICTION "
                        f"CHECK</span>", unsafe_allow_html=True)
            cf = A["conflict"]
            if cf.get("conflict") and ss["sel"] == winner_idx:
                st.error("**Contradicting signal found**\n\n"
                         f"- {cf['signal_a']}\n- {cf['signal_b']}\n\n"
                         "The same cause does not replicate across regions. "
                         "Weigh this before acting.")
            else:
                st.success("No contradicting signals across comparable "
                           "regions.")
        st.write("")
        b1, b2, _ = st.columns([1, 1.4, 2])
        b1.button("← Back", width="stretch", key=f"bk_{al['id']}",
                  on_click=lambda: ss.update(stage="rca_list"))
        b2.button("See Recommendation", type="primary", width="stretch",
                  key=f"sr_{al['id']}",
                  on_click=lambda: ss.update(stage="recommendation"))

    # ---------- Modal 4 : recommendation ----------
    elif ss["stage"] == "recommendation":
        rec = A["recommendation"]
        header_line()
        if ss["sel"] is not None and ss["sel"] < len(hyps) and \
                not hyps[ss["sel"]]["supported"]:
            st.info("You expanded a candidate that was rejected by the data — "
                    "the recommendation below follows the supported lead.")
        lead = next((x for x in hyps if x["supported"]), None)
        if lead:
            ltp, lcol = tier_pill(lead["confidence_pct"])
            st.markdown(f"Based on leading candidate **{lead['name']}** at "
                        f"<b style='color:{lcol}'>"
                        f"{lead['confidence_pct']}%</b> &nbsp;{ltp}",
                        unsafe_allow_html=True)
        st.subheader(rec["action"])
        if rec.get("est_impact_fmt"):
            st.markdown(f"Expected recovery: <b style='font-size:16px;"
                        f"color:{GOOD};'>{rec['est_impact_fmt']} / wk</b> "
                        f"<span style='color:{META};font-size:12px;'>"
                        f"({rec['basis']})</span>", unsafe_allow_html=True)
        else:
            st.caption("Basis: " + rec["basis"])

        with st.container(border=True):
            st.markdown(pill("LLM EXPLANATION · AUTO-AUDITED", VIOLET, TINT),
                        unsafe_allow_html=True)
            pkey = persona["llm_persona"]
            nkey = (al["id"], pkey)
            if nkey not in ss["narrations"]:
                payload = redact_for_cxo(dict(A)) \
                    if pkey == "CXO" else dict(A)
                text, eng = llm.narrate(payload, pkey)
                clean, removed, audit = llm.self_verify(text, payload)
                ss["narrations"][nkey] = {"clean": clean, "removed": removed,
                                          "engine": eng, "audit": audit}
            N = ss["narrations"][nkey]
            skey = ("stream", al["id"], pkey)
            if skey in ss["played"]:
                st.markdown(N["clean"])
            else:
                def typewriter(txt, chunk=2, tick=0.008):
                    for j in range(0, len(txt), chunk):
                        yield txt[:j + chunk]
                        time.sleep(tick)
                st.write_stream(typewriter(N["clean"]))
                ss["played"].add(skey)
            audit_pill = pill("✓ all claims verified", GOOD, GOOD_BG) \
                if not N["removed"] else \
                pill(f"⚠ {len(N['removed'])} unverified claim(s) removed",
                     LOW, LOW_BG)
            st.caption("Generated strictly from the verified JSON above · "
                       + audit_pill, unsafe_allow_html=True)

        reason = st.selectbox(
            "Before you decide — anything off?", ["", "Not enough evidence",
                                                  "Wrong cause identified",
                                                  "Already resolved",
                                                  "Other"],
            key=f"fb_{al['id']}")
        if reason == "Other":
            st.text_input("Tell us more", key=f"fbo_{al['id']}")

        f1, f2, _ = st.columns([1, 1, 2])
        f1.button("Approve", type="primary", width="stretch",
                  key=f"ap_{al['id']}",
                  on_click=make_decider(al["id"], al, route, "approved"))
        f2.button("Reject", width="stretch", key=f"rj_{al['id']}",
                  on_click=make_decider(al["id"], al, route, "rejected"))


if ss["open_aid"]:
    rca_modal()
