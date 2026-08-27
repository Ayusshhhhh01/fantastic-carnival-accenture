"""
CAUSE — Accenture Enterprise Causal Intelligence Platform.
Executive UI/UX Redesign conforming to the Accenture Brand & Design System:
- Accenture Signature Purple (#A100FF), Obsidian Corporate Accents, Chevron (>) Branding
- Zero-Scroll Box Sizing & Fluid Layout Geometry (No clipped boxes or internal scrollbars)
- High-Impact Executive KPI Summary Ribbon & Status Bar
- Modernized Altair Causal Visualizations with Translucent Gradients
- Stepped Interactive RCA Diagnostics with Audited Mathematical Verification
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

st.set_page_config(
    page_title="CAUSE | Accenture Causal Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ----------------------------------------------------------------- BRAND PALETTE --
ACCENT_PURPLE = "#7800C4"
ACCENT_PURPLE_DARK = "#540091"
ACCENT_PURPLE_LIGHT = "#F4E8FF"
ACCENT_PURPLE_BORDER = "#D8B4FE"
DARK_OBSIDIAN = "#0F0F14"
DARK_SLATE = "#1E1E28"
TEXT_PRIMARY = "#0F0F14"
TEXT_SECONDARY = "#242432"
TEXT_MUTED = "#555566"
LINE_BORDER = "#D4D7E0"
CARD_BG = "#FFFFFF"
SURFACE_BG = "#F4F5F8"

# Semantic Status Colors (WCAG AAA High Contrast)
GOOD, GOOD_BG, GOOD_BORDER = "#065F38", "#E6F9F0", "#8CE6B8"
CONF, CONF_BG, CONF_BORDER = "#9C140E", "#FEECEB", "#FCA5A0"
WARN, WARN_BG, WARN_BORDER = "#8A4B00", "#FFF7E6", "#FFD580"
INFO, INFO_BG, INFO_BORDER = "#0047B3", "#DEEBFF", "#A3C7FF"
MEDI, MEDI_BG, MEDI_BORDER = "#3B4A6B", "#EAEDF5", "#B8C4DC"  # neutral blue-grey, distinct from WARN amber

# ------------------------------------------------------------- ACCENTURE STYLES --
st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap');

html, body, [class*="css"], .stButton button, input, select, textarea {{
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
}}

/* Main canvas background */
.stApp {{
    background-color: {SURFACE_BG};
    color: {TEXT_PRIMARY};
}}

.block-container {{
    padding-top: 1.5rem !important;
    padding-bottom: 3rem !important;
    max-width: 1280px !important;
}}

/* Typography */
h1 {{
    font-size: 26px !important;
    font-weight: 800 !important;
    color: {TEXT_PRIMARY} !important;
    letter-spacing: -0.02em !important;
    margin-bottom: 0.35rem !important;
}}

h2 {{
    font-size: 20px !important;
    font-weight: 750 !important;
    color: {TEXT_PRIMARY} !important;
    letter-spacing: -0.01em !important;
}}

h3 {{
    font-size: 16px !important;
    font-weight: 700 !important;
    color: {TEXT_PRIMARY} !important;
}}

p, li {{
    font-size: 14px;
    color: {TEXT_SECONDARY};
    line-height: 1.55;
    font-weight: 500;
}}

/* Zero-scroll & Card Structure */
[data-testid="stVerticalBlockBorderWrapper"] {{
    background: {CARD_BG};
    border: 1px solid {LINE_BORDER} !important;
    border-radius: 12px !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    transition: transform 0.18s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.18s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.18s ease;
    overflow: visible !important;
}}

[data-testid="stVerticalBlockBorderWrapper"]:hover {{
    border-color: {ACCENT_PURPLE_BORDER} !important;
    box-shadow: 0 8px 24px rgba(120, 0, 196, 0.10);
    transform: translateY(-2px);
}}

/* Accenture Buttons */
.stButton > button {{
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-size: 13.5px !important;
    padding: 0.55rem 1.1rem !important;
    letter-spacing: 0.01em !important;
    transition: all 0.15s ease-in-out !important;
}}

.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {ACCENT_PURPLE} 0%, {ACCENT_PURPLE_DARK} 100%) !important;
    color: #FFFFFF !important;
    border: none !important;
    box-shadow: 0 2px 10px rgba(120, 0, 196, 0.32) !important;
}}

.stButton > button[kind="primary"]:hover {{
    background: linear-gradient(135deg, #8B00DC 0%, #6800B3 100%) !important;
    box-shadow: 0 4px 16px rgba(120, 0, 196, 0.45) !important;
    transform: translateY(-1px);
}}

.stButton > button[kind="secondary"] {{
    background: #FFFFFF !important;
    color: {TEXT_PRIMARY} !important;
    border: 1.5px solid {TEXT_PRIMARY} !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
}}

.stButton > button[kind="secondary"]:hover {{
    border-color: {ACCENT_PURPLE} !important;
    color: {ACCENT_PURPLE_DARK} !important;
    background: {ACCENT_PURPLE_LIGHT} !important;
}}

/* Custom Progress Bar */
[data-testid="stProgress"] > div {{
    background: #EAECEF !important;
    border-radius: 99px !important;
    height: 8px !important;
}}

[data-testid="stProgress"] > div > div {{
    background: linear-gradient(90deg, {ACCENT_PURPLE} 0%, #00D2FF 100%) !important;
    border-radius: 99px !important;
}}

/* Dialog & Modal */
div[data-testid="stDialog"] div[role="dialog"] {{
    border-radius: 16px !important;
    border: 1px solid {LINE_BORDER} !important;
    box-shadow: 0 24px 64px rgba(15, 15, 20, 0.22) !important;
    max-width: 880px !important;
    background: #FFFFFF !important;
}}

div[data-testid="stDialog"] div[role="dialog"]::before {{
    content: '';
    position: fixed;
    inset: 0;
    background: rgba(15, 15, 20, 0.65);
    backdrop-filter: blur(4px);
}}

/* Inputs */
.stSelectbox, .stTextInput {{
    font-size: 13.5px !important;
}}

hr {{
    border-color: {LINE_BORDER} !important;
    margin: 1.25rem 0 !important;
}}
</style>""", unsafe_allow_html=True)

# ------------------------------------------------------------- SESSION STATE ----
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
    "cm_elex": {
        "name": "Category Manager", "scope": "Electronics",
        "short": "CM · Electronics", "mono": "EL",
        "cats": ["Electronics"], "llm_persona": "Category Manager",
        "desc": "Portfolio SKU availability, warehouse inventory & supplier stockouts."
    },
    "cm_home": {
        "name": "Category Manager", "scope": "Apparel & Home",
        "short": "CM · Apparel & Home", "mono": "AH",
        "cats": ["Apparel", "Home & Kitchen"],
        "llm_persona": "Category Manager",
        "desc": "Multi-category promotional spend, regional campaigns & price elasticities."
    },
    "cxo": {
        "name": "Chief Executive Officer", "scope": "Enterprise Portfolio",
        "short": "CXO Suite", "mono": "CX",
        "cats": None, "top_n": 3,
        "llm_persona": "CXO",
        "desc": "Cross-category enterprise risk triage, net revenue impact & strategic directives."
    },
}

ROUTE_LABEL = {
    "RESOLVED": "Diagnosed",
    "FAST_PATH": "Direct Match",
    "UNRESOLVED_CONFLICT": "Conflict",
    "ABSTAIN": "Low Evidence"
}

# ------------------------------------------------------------- UI COMPONENT HELPERS ----
def pill(text, fg, bg, border="transparent", icon=""):
    icon_html = f"<span style='margin-right:4px;'>{icon}</span>" if icon else ""
    return (f"<span style='background:{bg};color:{fg};border:1px solid {border};"
            f"padding:3px 10px;border-radius:99px;font-size:11px;font-weight:750;"
            f"letter-spacing:0.03em;display:inline-flex;align-items:center;white-space:nowrap;'>"
            f"{icon_html}{text}</span>")


def tier_pill(p):
    if p >= 75:
        return pill("HIGH CONFIDENCE", GOOD, GOOD_BG, GOOD_BORDER, "✓"), GOOD
    if p >= 50:
        return pill("MEDIUM CONFIDENCE", MEDI, MEDI_BG, MEDI_BORDER, "●"), MEDI
    return pill("LOW CONFIDENCE", CONF, CONF_BG, CONF_BORDER, "!"), CONF


def severity_hex(a):
    if a["route"] == "UNRESOLVED_CONFLICT":
        return CONF
    if a["route"] == "ABSTAIN":
        return WARN
    return CONF if abs(a["alert"]["delta_inr"]) >= 25e5 else \
        (WARN if abs(a["alert"]["delta_inr"]) >= 10e5 else GOOD)


def route_pill(route):
    m = {
        "RESOLVED": (GOOD, GOOD_BG, GOOD_BORDER, "●"),
        "FAST_PATH": (ACCENT_PURPLE_DARK, ACCENT_PURPLE_LIGHT, ACCENT_PURPLE_BORDER, "⚡"),
        "UNRESOLVED_CONFLICT": (CONF, CONF_BG, CONF_BORDER, "⚠"),
        "ABSTAIN": (WARN, WARN_BG, WARN_BORDER, "◌")
    }
    fg, bg, bd, ic = m.get(route, (TEXT_MUTED, SURFACE_BG, LINE_BORDER, ""))
    return pill(ROUTE_LABEL.get(route, route), fg, bg, bd, ic)


def verification_rate():
    """% of narrations generated this session with zero unsupported claims removed."""
    all_narrations = ss.get("narrations", {})
    if not all_narrations:
        return None  # nothing generated yet this session
    total = len(all_narrations)
    clean = sum(1 for n in all_narrations.values() if not n.get("removed"))
    return round(clean / total * 100)


def alerts_for(pid):
    p = PERSONAS[pid]
    if p["cats"] is None:
        top = sorted(ALERTS, key=lambda x: -abs(x["alert"]["delta_inr"]))
        return top[:p["top_n"]]
    return [a for a in ALERTS if a["alert"]["category"] in p["cats"]]


def ranked_hyps(A):
    return sorted(A["hypotheses"], key=lambda h: h["confidence_pct"], reverse=True)


# ------------------------------------------------------------- CHARTS & DATA ----
@st.cache_data
def _frames():
    d = Path("cause/data")
    s = pd.read_csv(d / "sales_daily.csv", parse_dates=["date"])
    c = pd.read_csv(d / "campaigns_weekly.csv", parse_dates=["week_start"])
    return s, c


def _axis_accenture(chart):
    return (chart.configure_view(stroke=None)
            .configure_axis(
                gridColor="#EDEFF2",
                labelColor=TEXT_MUTED,
                titleColor=TEXT_MUTED,
                domain=False,
                labelFont="Plus Jakarta Sans",
                titleFont="Plus Jakarta Sans"
            ))


def snapshot_alert_chart(A, height=210):
    a = A["alert"]
    if a["kpi"] == "Marketing Spend":
        _, c = _frames()
        w = (c[c.category.eq(a["category"])].groupby("week_start", as_index=False)["spend"]
             .sum().sort_values("week_start").tail(8)
             .rename(columns={"week_start": "week", "spend": "value"}))
    else:
        s, _ = _frames()
        m = s.category.eq(a["category"])
        if a["region"] != "(all)":
            m &= s.region.eq(a["region"])
        d = s[m].copy()
        d["week"] = d["date"] - pd.to_timedelta(d["date"].dt.dayofweek, unit="D")
        w = (d.groupby("week", as_index=False)["revenue"].sum()
             .sort_values("week").tail(8)
             .rename(columns={"revenue": "value"}))

    hl = pd.Timestamp(a["week_start"])
    ytitle = "Spend / Wk (₹)" if a["kpi"] == "Marketing Spend" else "Revenue / Wk (₹)"
    
    band = alt.Chart(pd.DataFrame({"s": [hl], "e": [hl + pd.Timedelta(days=7)]})).mark_rect(
        color="#9C140E14",
        stroke="#9C140E55",
        strokeWidth=1,
        strokeDash=[3, 3]
    ).encode(x="s:T", x2="e:T")

    area = alt.Chart(w).mark_area(
        color=alt.Gradient(
            gradient="linear",
            stops=[
                alt.GradientStop(color="#7800C433", offset=0),
                alt.GradientStop(color="#7800C400", offset=1)
            ],
            x1=1, x2=1, y1=0, y2=1
        )
    ).encode(
        x=alt.X("week:T", title=None, axis=alt.Axis(format="%b %d")),
        y=alt.Y("value:Q", title=ytitle, axis=alt.Axis(format="~s"))
    )

    line = alt.Chart(w).mark_line(
        color=ACCENT_PURPLE,
        strokeWidth=2.5,
        point=alt.OverlayMarkDef(color=ACCENT_PURPLE, size=45, filled=True)
    ).encode(
        x=alt.X("week:T", title=None),
        y=alt.Y("value:Q", title=ytitle)
    )

    st.altair_chart(_axis_accenture(band + area + line).properties(height=height), width="stretch")


def snapshot_hyp_chart(A, h, height=150):
    a = A["alert"]
    d = h.get("detail") or {}
    s, c = _frames()

    if h["name"].startswith("Supply") and d.get("product_id"):
        dd = s[(s.product_id == d["product_id"]) & (s.region == a["region"])].sort_values("date").tail(14)
        so = set(map(pd.Timestamp, d.get("stockout_days", [])))
        dd = dd.assign(state=dd.date.map(lambda x: "Stock-out" if x in so else "Normal"))
        ch = alt.Chart(dd).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
            x=alt.X("date:T", title=None, axis=alt.Axis(labelAngle=-45, format="%b %d")),
            y=alt.Y("revenue:Q", title=None, axis=alt.Axis(format="~s")),
            color=alt.Color("state:N", scale=alt.Scale(
                domain=["Normal", "Stock-out"],
                range=["#D8DCE3", CONF]), legend=None),
            tooltip=["date:T", "revenue:Q", "state:N"]
        )
        st.altair_chart(_axis_accenture(ch).properties(height=height), width="stretch")

    elif h["name"].startswith("Demand"):
        cc = c[c.category.eq(a["category"])]
        if a["region"] != "(all)":
            cc = cc[cc.region.eq(a["region"])]
        w = cc.groupby("week_start", as_index=False)["spend"].sum().sort_values("week_start").tail(8)
        w["flag"] = ["Breach Week" if x == pd.Timestamp(a["week_start"]) else "Prior" for x in w.week_start]
        ch = alt.Chart(w).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
            x=alt.X("week_start:T", title=None, axis=alt.Axis(labelAngle=-45, format="%b %d")),
            y=alt.Y("spend:Q", title=None, axis=alt.Axis(format="~s")),
            color=alt.Color("flag:N", scale=alt.Scale(
                domain=["Prior", "Breach Week"],
                range=["#D8DCE3", ACCENT_PURPLE]), legend=None),
            tooltip=["week_start:T", "spend:Q", "flag:N"]
        )
        st.altair_chart(_axis_accenture(ch).properties(height=height), width="stretch")

    elif h["name"].startswith("Pricing"):
        m = s.category.eq(a["category"])
        if a["region"] != "(all)":
            m &= s.region.eq(a["region"])
        dd = s[m].groupby("date", as_index=False)["unit_price"].mean().sort_values("date").tail(21)
        ch = alt.Chart(dd).mark_line(color=ACCENT_PURPLE, strokeWidth=2.2).encode(
            x=alt.X("date:T", title=None, axis=alt.Axis(labelAngle=-45, format="%b %d")),
            y=alt.Y("unit_price:Q", title=None, axis=alt.Axis(format="~s")),
            tooltip=["date:T", "unit_price:Q"]
        )
        st.altair_chart(_axis_accenture(ch).properties(height=height), width="stretch")
    else:
        snapshot_alert_chart(A, height=height)


def conf_bar(pct):
    c1, c2 = st.columns([3.2, 1])
    with c1:
        st.progress(min(pct, 100) / 100.0)
    with c2:
        tp, tcol = tier_pill(pct)
        st.markdown(f"<div style='text-align:right;font-size:13.5px;font-weight:800;color:{tcol};'>{pct}%</div>", unsafe_allow_html=True)


def flash_toast():
    if ss.get("flash"):
        st.toast(ss.pop("flash"), icon="⚡")


# =========================================================== 1. ACCENTURE LANDING / LOGIN SCREEN ==
current_persona = ss.get("current_persona")
if current_persona not in PERSONAS:
    ss["current_persona"] = None
    st.write("")
    # Top Accenture Brand Ribbon
    st.markdown(f"""
    <div style='text-align:center;padding:24px 0 16px;'>
        <div style='display:inline-flex;align-items:center;gap:10px;background:#FFFFFF;border:1px solid {LINE_BORDER};padding:6px 16px;border-radius:99px;box-shadow:0 2px 8px rgba(0,0,0,0.03);margin-bottom:18px;'>
            <span style='font-weight:800;letter-spacing:-0.5px;color:#0F0F14;font-size:13px;'>accenture</span>
            <span style='color:{ACCENT_PURPLE};font-weight:800;font-size:15px;'>&gt;</span>
            <span style='font-size:11px;font-weight:700;color:{TEXT_MUTED};letter-spacing:0.06em;text-transform:uppercase;'>Applied Intelligence</span>
        </div>
        <h1 style='font-size:36px !important;font-weight:800;letter-spacing:-0.03em;color:{TEXT_PRIMARY};margin:0;'>
            CAUSE <span style='color:{ACCENT_PURPLE};font-size:36px;'>&gt;</span> Causal Intelligence
        </h1>
        <p style='color:{TEXT_SECONDARY};font-size:15.5px;max-width:680px;margin:10px auto 0;line-height:1.5;font-weight:500;'>
            Every retail anomaly diagnosed at the root. Every number mathematically verified against enterprise telemetry. Nothing taken on faith.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    
    # 3 Persona Cards Grid - Uniform Primary Purple Buttons
    cols = st.columns(3, gap="medium")
    for col, (pid, p) in zip(cols, PERSONAS.items()):
        with col, st.container(border=True):
            st.markdown(f"""
            <div style='padding:10px 4px 14px;'>
                <div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;'>
                    <div style='width:46px;height:46px;border-radius:12px;background:{ACCENT_PURPLE_LIGHT};border:1.5px solid {ACCENT_PURPLE_BORDER};color:{ACCENT_PURPLE_DARK};font-weight:800;font-size:17px;display:flex;align-items:center;justify-content:center;'>
                        {p['mono']}
                    </div>
                    {pill(p['scope'], ACCENT_PURPLE_DARK, ACCENT_PURPLE_LIGHT, ACCENT_PURPLE_BORDER)}
                </div>
                <div style='font-weight:800;font-size:18px;color:{TEXT_PRIMARY};margin-bottom:6px;'>{p['name']}</div>
                <div style='color:{TEXT_SECONDARY};font-size:13.5px;min-height:52px;line-height:1.5;font-weight:500;'>{p['desc']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Enter", key=f"login_{pid}", width="stretch", type="primary"):
                ss["current_persona"] = pid
                ss["flash"] = None
                st.rerun()

    st.write("")
    st.markdown(f"""
    <div style='background:#FFFFFF;border:1px solid {LINE_BORDER};border-radius:12px;padding:14px 20px;display:flex;align-items:center;justify-content:space-around;flex-wrap:wrap;gap:12px;box-shadow:0 2px 6px rgba(0,0,0,0.02);'>
        <div style='display:flex;align-items:center;gap:8px;font-size:13px;color:{TEXT_PRIMARY};font-weight:700;'>
            <span style='color:{GOOD};font-size:15px;'>✓</span> Deterministic Causal Inference
        </div>
        <div style='display:flex;align-items:center;gap:8px;font-size:13px;color:{TEXT_PRIMARY};font-weight:700;'>
            <span style='color:{ACCENT_PURPLE};font-size:15px;'>⚡</span> Zero-Hallucination LLM Audit
        </div>
        <div style='display:flex;align-items:center;gap:8px;font-size:13px;color:{TEXT_PRIMARY};font-weight:700;'>
            <span style='color:{INFO};font-size:15px;'>◈</span> Enterprise Telemetry Ground Truth
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# =========================================================== 2. ACCENTURE EXECUTIVE DASHBOARD ==
current_persona = ss.get("current_persona")
if current_persona not in PERSONAS:
    st.stop()

persona = PERSONAS[current_persona]
flash_toast()
my_alerts = alerts_for(current_persona)
active = [a for a in my_alerts if a["alert"]["id"] not in ss["handled"]]
handled_ids = [a["alert"]["id"] for a in my_alerts if a["alert"]["id"] in ss["handled"]]

# Top Navigation Bar
nav_col1, nav_col2 = st.columns([4, 1.2])
with nav_col1:
    st.markdown(f"""
    <div style='display:flex;align-items:center;gap:10px;margin-bottom:4px;'>
        <span style='font-weight:800;letter-spacing:-0.5px;color:#0F0F14;font-size:16px;'>accenture</span>
        <span style='color:{ACCENT_PURPLE};font-weight:800;font-size:18px;'>&gt;</span>
        <span style='font-weight:800;font-size:16px;color:{TEXT_PRIMARY};letter-spacing:-0.02em;'>CAUSE</span>
        <span style='background:{ACCENT_PURPLE_LIGHT};color:{ACCENT_PURPLE_DARK};border:1px solid {ACCENT_PURPLE_BORDER};font-size:11px;font-weight:750;padding:2px 10px;border-radius:99px;letter-spacing:0.02em;'>{persona['short']}</span>
    </div>
    """, unsafe_allow_html=True)
with nav_col2:
    st.button("Switch persona", width="stretch", on_click=lambda: ss.update(current_persona=None))

# Executive KPI Ribbon
tot_impact = sum(abs(a["alert"]["delta_inr"]) for a in active)
high_conf_cnt = len([a for a in active if a["route"] in ("RESOLVED", "FAST_PATH")])
scope_txt = ("All categories" if current_persona == "cxo" else " & ".join(persona["cats"]))

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1, st.container(border=True):
    st.markdown(f"""
    <div style='padding:2px;'>
        <div style='font-size:11px;font-weight:750;color:{TEXT_MUTED};letter-spacing:0.05em;text-transform:uppercase;'>Active Signals</div>
        <div style='font-size:24px;font-weight:800;color:{TEXT_PRIMARY};margin:4px 0 1px;'>{len(active)} <span style='font-size:13px;font-weight:600;color:{TEXT_MUTED};'>Unresolved</span></div>
        <div style='font-size:12px;color:{TEXT_SECONDARY};font-weight:500;'>{scope_txt}</div>
    </div>
    """, unsafe_allow_html=True)

with kpi2, st.container(border=True):
    st.markdown(f"""
    <div style='padding:2px;'>
        <div style='font-size:11px;font-weight:750;color:{TEXT_MUTED};letter-spacing:0.05em;text-transform:uppercase;'>Materiality Exposure</div>
        <div style='font-size:24px;font-weight:800;color:{CONF};margin:4px 0 1px;'>{fmt_inr(tot_impact)}</div>
        <div style='font-size:12px;color:{TEXT_SECONDARY};font-weight:500;'>Week of {P['cur_week']}</div>
    </div>
    """, unsafe_allow_html=True)

with kpi3, st.container(border=True):
    conf_pct = round((high_conf_cnt / len(active) * 100)) if active else 100
    st.markdown(f"""
    <div style='padding:2px;'>
        <div style='font-size:11px;font-weight:750;color:{TEXT_MUTED};letter-spacing:0.05em;text-transform:uppercase;'>Auto-Diagnostic Rate</div>
        <div style='font-size:24px;font-weight:800;color:{GOOD};margin:4px 0 1px;'>{conf_pct}%</div>
        <div style='font-size:12px;color:{TEXT_SECONDARY};font-weight:500;'>{high_conf_cnt} of {len(active)} signals verified</div>
    </div>
    """, unsafe_allow_html=True)

with kpi4, st.container(border=True):
    vrate = verification_rate()
    vrate_display = f"{vrate}%" if vrate is not None else "—"
    vrate_caption = (f"{sum(1 for n in ss['narrations'].values() if not n.get('removed'))} of {len(ss['narrations'])} narrations clean"
                     if vrate is not None else "No diagnoses run yet this session")
    st.markdown(f"""
    <div style='padding:2px;'>
        <div style='font-size:11px;font-weight:750;color:{TEXT_MUTED};letter-spacing:0.05em;text-transform:uppercase;'>Narrative Verification Rate</div>
        <div style='font-size:24px;font-weight:800;color:{ACCENT_PURPLE_DARK};margin:4px 0 1px;'>{vrate_display}</div>
        <div style='font-size:12px;color:{TEXT_SECONDARY};font-weight:500;'>{vrate_caption}</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# KPI Semantic Registry Expander
with st.expander("◈ KPI Semantic Layer & Lineage Contracts (5 Connected KPIs Across Telemetry Grains)", expanded=False):
    for kpi_key, kpi_meta in P.get("kpi_registry", {}).items():
        st.markdown(f"**{kpi_meta['display_name']}** &nbsp; <code style='font-size:11.5px;'>{kpi_meta['formula']}</code>", unsafe_allow_html=True)
        st.caption(f"Grain: {kpi_meta['grain']} · Source: {kpi_meta['source_table']} · Baseline: {kpi_meta['baseline_method']} · Materiality: {kpi_meta['materiality_rule']}")
        st.caption(f"Connected Drivers: {', '.join(kpi_meta['connected_drivers'])} · Access: {kpi_meta['access_entitlement'].get(persona['name'], 'Standard')}")
        st.divider()

# Section Header
if active:
    n = len(active)
    st.markdown(f"""
    <div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;'>
        <h2 style='margin:0;'>Telemetry Anomaly Queue <span style='color:{ACCENT_PURPLE_DARK};font-size:18px;'>({n})</span></h2>
        <div style='font-size:12.5px;color:{TEXT_MUTED};font-weight:600;'>Week of {P['cur_week']} · ranked by ₹ impact · {scope_txt}</div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div style='background:#FFFFFF;border:1px solid {GOOD_BORDER};border-radius:12px;padding:32px;text-align:center;box-shadow:0 2px 10px rgba(0,0,0,0.02);'>
        <div style='font-size:32px;margin-bottom:8px;'>✓</div>
        <h2 style='color:{GOOD};margin:0 0 6px;'>All clear</h2>
        <p style='color:{TEXT_SECONDARY};margin:0;font-weight:500;'>Week of {P['cur_week']} — nothing left in your scope.</p>
    </div>
    """, unsafe_allow_html=True)

# Responsive 3-Column Card Grid (Zero-Scroll Auto Fitting Layout)
if active:
    nrows = -(-len(active) // 3)
    rows = [st.columns(3, gap="medium") for _ in range(nrows)]
    for i, A in enumerate(active):
        al = A["alert"]
        col = rows[i // 3][i % 3]
        pct = al["pct_change"]
        pct_txt = "new" if pct is None else f"{pct * 100:+.1f}%"
        arrow = "▲" if (pct is not None and pct > 0) else ("▼" if (pct is not None and pct < 0) else "●")
        sev = severity_hex(A)
        region_txt = f" · {al['region'].replace('Region ', '')}" if al['region'] != '(all)' else ""
        
        with col, st.container(border=True):
            # Top card header
            st.markdown(f"""
            <div style='padding:2px 2px 6px;'>
                <div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;'>
                    {route_pill(A['route'])}
                    <span style='font-size:11.5px;font-weight:700;color:{TEXT_MUTED};'>{al['category']}{region_txt}</span>
                </div>
                <div style='font-size:16px;font-weight:800;color:{TEXT_PRIMARY};margin-bottom:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>
                    {al['kpi']} · {al['category']}{region_txt}
                </div>
                <div style='background:{SURFACE_BG};border:1px solid {LINE_BORDER};border-radius:8px;padding:10px 12px;margin-bottom:14px;'>
                    <div style='display:flex;align-items:center;justify-content:space-between;'>
                        <div>
                            <div style='font-size:10.5px;font-weight:750;color:{TEXT_MUTED};text-transform:uppercase;letter-spacing:0.04em;'>vs 4-wk baseline</div>
                            <div style='font-size:22px;font-weight:800;color:{sev};line-height:1.2;margin-top:2px;'>
                                {arrow} {pct_txt}
                            </div>
                        </div>
                        <div style='text-align:right;'>
                            <div style='font-size:10.5px;font-weight:750;color:{TEXT_MUTED};text-transform:uppercase;letter-spacing:0.04em;'>Financial Impact</div>
                            <div style='font-size:18px;font-weight:800;color:{TEXT_PRIMARY};line-height:1.2;margin-top:2px;'>
                                {al['delta_fmt']}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.button(
                "Investigate",
                key=f"card_{al['id']}",
                width="stretch",
                type="primary",
                on_click=lambda aid=al["id"]: ss.update(open_aid=aid, stage="detail", sel=0)
            )

# Handled / Resolved Log Ticker
if handled_ids:
    st.divider()
    chips = " ".join(
        f"<span style='background:#FFFFFF;border:1px solid {LINE_BORDER};"
        f"color:{TEXT_PRIMARY};padding:3px 11px;border-radius:99px;font-size:12px;font-weight:600;'>"
        f"{i} · {ss['handled'][i]['decision']}</span>" for i in handled_ids)
    st.markdown(f"<span style='color:{TEXT_MUTED};font-size:12px;font-weight:700;'>Recently handled</span> &nbsp;" + chips, unsafe_allow_html=True)


# =========================================================== 3. ACCENTURE RCA MODAL FLOW ==
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


@st.dialog("Root Cause Diagnostic Intelligence", width="large")
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
            st.subheader(f"{al['kpi']} — {al['category']} — new signal, no baseline")
        else:
            st.subheader(f"{al['kpi']} — {al['category']}"
                         + (f" — {al['region']}" if al["region"] != "(all)" else "")
                         + f" — {direction} {abs(al['pct_change']) * 100:.1f}%")
        st.caption(f"Impact {al['delta_fmt']} · z={al['z_fmt']} · week {al['week_start']}")

    # ------------------ Step 1 : Detail Overview ------------------
    if ss["stage"] == "detail":
        header_line()
        snapshot_alert_chart(A, height=210)
        st.caption("Weekly KPI trend · shaded band marks the week that breached the materiality rule (|z| ≥ 1.5 and |Δ| ≥ 10%)")
        
        st.write("")
        b1, b2, _ = st.columns([1.4, 1.2, 2])
        b1.button("Diagnose", type="primary", width="stretch", key=f"d_{al['id']}",
                  on_click=lambda: ss.update(stage="diagnosing"))
        b2.button("Ignore", width="stretch", key=f"ig_{al['id']}",
                  help="Removes this alert from your queue",
                  on_click=make_ignorer(al["id"]))

    # ------------------ Step 2 : Automated Triage Scan (Path 1 -> Path 2) ------------------
    elif ss["stage"] == "diagnosing":
        key = ("diag", al["id"])
        if key not in ss["played"]:
            fp = A["fast_path"]
            
            st.subheader("Automated Triage Scan")
            st.caption("Dual-path diagnostic evaluation: Direct Event Match (Path 1) → Deep Causal Inference (Path 2)")
            
            p1_box = st.empty()
            p2_box = st.empty()
            
            # --- Path 1: Direct Match Scan ---
            if fp:
                p1_box.markdown(f"""
                <div style='background:#FFFFFF;border:1.5px solid {ACCENT_PURPLE_BORDER};border-radius:10px;padding:12px 16px;margin-bottom:10px;'>
                    <div style='display:flex;justify-content:space-between;align-items:center;'>
                        <div style='font-size:12px;font-weight:750;color:{ACCENT_PURPLE_DARK};letter-spacing:0.04em;'>PATH 1 · DIRECT EVENT MATCH</div>
                        <span style='background:{GOOD_BG};color:{GOOD};font-size:11px;font-weight:750;padding:2px 8px;border-radius:99px;border:1px solid {GOOD_BORDER};'>MATCH FOUND</span>
                    </div>
                    <div style='font-size:13.5px;font-weight:700;color:{TEXT_PRIMARY};margin-top:6px;'>
                        ✓ Direct operational event matched: [{fp['event_type']}] on {fp['event_date']}
                    </div>
                    <div style='font-size:12px;color:{TEXT_MUTED};margin-top:2px;'>
                        {fp['description']} — Bypassing Path 2 to Recommendation
                    </div>
                </div>
                """, unsafe_allow_html=True)
                time.sleep(0.5)
            else:
                p1_box.markdown(f"""
                <div style='background:#FFFFFF;border:1px solid {LINE_BORDER};border-radius:10px;padding:12px 16px;margin-bottom:10px;'>
                    <div style='display:flex;justify-content:space-between;align-items:center;'>
                        <div style='font-size:12px;font-weight:750;color:{TEXT_MUTED};letter-spacing:0.04em;'>PATH 1 · DIRECT EVENT MATCH</div>
                        <span style='background:{SURFACE_BG};color:{TEXT_MUTED};font-size:11px;font-weight:750;padding:2px 8px;border-radius:99px;border:1px solid {LINE_BORDER};'>NO MATCH</span>
                    </div>
                    <div style='font-size:13px;font-weight:600;color:{TEXT_SECONDARY};margin-top:6px;'>
                        Scanning operational change log... <span style='color:{TEXT_MUTED};'>No direct event found</span>
                    </div>
                    <div style='font-size:12px;color:{TEXT_MUTED};margin-top:2px;'>
                        Escalating to Path 2: Deep Causal Analysis
                    </div>
                </div>
                """, unsafe_allow_html=True)
                time.sleep(0.3)
                
                # --- Path 2: Deep Causal Inference ---
                res_txt = "Insufficient Evidence (Abstain)" if route == "ABSTAIN" else \
                    ("Contradiction Flagged" if route == "UNRESOLVED_CONFLICT" else "Causal Analysis Complete")
                badge_bg = WARN_BG if route == "ABSTAIN" else (CONF_BG if route == "UNRESOLVED_CONFLICT" else GOOD_BG)
                badge_fg = WARN if route == "ABSTAIN" else (CONF if route == "UNRESOLVED_CONFLICT" else GOOD)
                badge_bd = WARN_BORDER if route == "ABSTAIN" else (CONF_BORDER if route == "UNRESOLVED_CONFLICT" else GOOD_BORDER)
                
                p2_box.markdown(f"""
                <div style='background:#FFFFFF;border:1.5px solid {ACCENT_PURPLE_BORDER};border-radius:10px;padding:12px 16px;'>
                    <div style='display:flex;justify-content:space-between;align-items:center;'>
                        <div style='font-size:12px;font-weight:750;color:{ACCENT_PURPLE_DARK};letter-spacing:0.04em;'>PATH 2 · DEEP CAUSAL INFERENCE</div>
                        <span style='background:{badge_bg};color:{badge_fg};font-size:11px;font-weight:750;padding:2px 8px;border-radius:99px;border:1px solid {badge_bd};'>{res_txt.upper()}</span>
                    </div>
                    <div style='margin-top:8px;font-size:12.5px;color:{TEXT_PRIMARY};display:flex;flex-direction:column;gap:4px;'>
                        <div><span style='color:{GOOD};font-weight:800;'>✓</span> Multi-source evidence retrieved across POS, CRM, ERP & logs</div>
                        <div><span style='color:{GOOD};font-weight:800;'>✓</span> 4 competing hypotheses tested & counterfactuals evaluated</div>
                        <div><span style='color:{GOOD};font-weight:800;'>✓</span> Weighted evidence confidence scored & cross-region contradiction evaluated</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                time.sleep(0.5)

            ss["played"].add(key)
            if fp:
                ss.update(stage="recommendation", sel=None)
            elif route == "ABSTAIN":
                ss["stage"] = "abstain"
            else:
                ss.update(stage="rca_list", sel=0)
            st.rerun()

    # ------------------ Step 3 : Abstention Fallback ------------------
    elif ss["stage"] == "abstain":
        header_line()
        abst = A.get("abstention", {})
        with st.container(border=True):
            st.markdown(pill("INSUFFICIENT EVIDENCE", WARN, WARN_BG, WARN_BORDER, "⚠"), unsafe_allow_html=True)
            st.write("")
            st.warning(f"**Diagnostic Abstention:** {abst.get('reason', 'Insufficient baseline data.')}\n\n"
                       f"• **Missing Telemetry:** {abst.get('missing_data', 'Sparse history.')}\n"
                       f"• **Required Data:** {abst.get('required_data', 'Collect further observations.')}")
            st.caption("The pipeline stopped here by design — CAUSE will not generate an explanation the data cannot support. No LLM was called.")
        st.write("")
        if st.button("← Back to Dashboard", type="primary", width="stretch"):
            close()

    # ------------------ Step 4 : Hypothesis Ranking Matrix ------------------
    elif ss["stage"] == "rca_list":
        header_line()
        if route == "UNRESOLVED_CONFLICT":
            st.markdown(pill("CONFLICTING SIGNALS — REVIEW BEFORE ACTING", CONF, CONF_BG, CONF_BORDER),
                        unsafe_allow_html=True)
            st.caption("Comparable regions show contradicting outcomes for the leading "
                       "cause. Expand it below for details before approving any action.")
            st.write("")
        st.caption("Confidence = weighted combination of temporal correlation, source reliability, hypothesis margin, and data completeness.")
        
        for i, h in enumerate(hyps):
            tp, tcol = tier_pill(h["confidence_pct"])
            badge = pill("SUPPORTED", GOOD, GOOD_BG, GOOD_BORDER, "✓") if h["supported"] \
                else pill("REJECTED", CONF, CONF_BG, CONF_BORDER, "✕")
            one_liner = h["verdict"].split(" - ")[0]
            
            with st.container(border=True):
                c1, c2, c3 = st.columns([4.6, 2.2, 1.2])
                with c1:
                    c1.markdown(f"**{i + 1}. {h['name']}**&nbsp;&nbsp;{badge}", unsafe_allow_html=True)
                    c1.caption(one_liner)
                with c2:
                    conf_bar(h["confidence_pct"])
                with c3:
                    c3.markdown(tp, unsafe_allow_html=True)
                    c3.button("Expand", key=f"ex_{al['id']}_{i}", width="stretch",
                              on_click=lambda i=i: ss.update(stage="rca_expand", sel=i))

        st.divider()
        _, mid, _ = st.columns([1, 2, 1])
        mid.button("Continue →", type="primary", width="stretch",
                   key=f"cont_{al['id']}", on_click=lambda: ss.update(sel=0, stage="recommendation"))

    # ------------------ Step 5 : Candidate Deep Dive ------------------
    elif ss["stage"] == "rca_expand":
        h = hyps[ss["sel"]]
        winner_idx = next((i for i, x in enumerate(hyps) if x["supported"]), 0)
        tp, _ = tier_pill(h["confidence_pct"])
        badge = pill("SUPPORTED", GOOD, GOOD_BG, GOOD_BORDER, "✓") if h["supported"] \
            else pill("REJECTED", CONF, CONF_BG, CONF_BORDER, "✕")
        
        header_line()
        st.markdown(f"Candidate {ss['sel'] + 1}/{len(hyps)} &nbsp;{badge} &nbsp;{tp}", unsafe_allow_html=True)
        
        row1_col1, row1_col2 = st.columns(2, gap="medium")
        with row1_col1, st.container(border=True):
            st.markdown(f"<span style='font-size:12px;font-weight:800;color:{ACCENT_PURPLE_DARK};letter-spacing:.05em;text-transform:uppercase;'>VERDICT</span>", unsafe_allow_html=True)
            st.write(h["verdict"])
            st.caption("Source: " + h["data_source"])
            
        with row1_col2, st.container(border=True):
            st.markdown(f"<span style='font-size:12px;font-weight:800;color:{ACCENT_PURPLE_DARK};letter-spacing:.05em;text-transform:uppercase;'>DATA SNAPSHOT</span>", unsafe_allow_html=True)
            snapshot_hyp_chart(A, h, height=140)

        row2_col1, row2_col2 = st.columns(2, gap="medium")
        with row2_col1, st.container(border=True):
            st.markdown(f"<span style='font-size:12px;font-weight:800;color:{ACCENT_PURPLE_DARK};letter-spacing:.05em;text-transform:uppercase;'>WEIGHTED EVIDENCE BREAKDOWN</span>", unsafe_allow_html=True)
            w = h["weights"]; f = h["factors"]
            for k in ("temporal_correlation", "source_agreement", "hypothesis_margin", "data_completeness"):
                sym, lbl = FACTOR_LABELS[k]
                fv = round(f[k] * 100)
                st.markdown(f"<span style='color:{TEXT_MUTED};font-size:12px;font-weight:600;'>{sym} {w[k]:.2f} × {lbl}</span><span style='float:right;color:{TEXT_PRIMARY};font-size:12px;font-weight:750;'>&nbsp;&nbsp;= {fv}% × {w[k]:.2f}</span>", unsafe_allow_html=True)
            st.write("")
            conf_bar(h["confidence_pct"])

        with row2_col2, st.container(border=True):
            st.markdown(f"<span style='font-size:12px;font-weight:800;color:{ACCENT_PURPLE_DARK};letter-spacing:.05em;text-transform:uppercase;'>CONTRADICTION CHECK</span>", unsafe_allow_html=True)
            cf = A["conflict"]
            if cf.get("conflict") and ss["sel"] == winner_idx:
                st.error("**Contradicting signal found**\n\n"
                         f"- {cf['signal_a']}\n- {cf['signal_b']}\n\n"
                         "The same cause does not replicate across regions. "
                         "Weigh this before acting.")
            else:
                st.success("No contradicting signals across comparable regions.")

        # Multi-Source Evidence Citations
        cites = h.get("rag_citations") or A.get("rag_evidence", [])
        if cites:
            st.write("")
            with st.container(border=True):
                st.markdown(f"<span style='font-size:12px;font-weight:800;color:{ACCENT_PURPLE_DARK};letter-spacing:.05em;text-transform:uppercase;'>RETRIEVED MULTI-SOURCE EVIDENCE</span>", unsafe_allow_html=True)
                for rc in cites[:3]:
                    st.markdown(f"""
                    <div style='background:{SURFACE_BG};border:1px solid {LINE_BORDER};border-radius:6px;padding:6px 10px;margin-bottom:6px;font-size:12px;'>
                        <div style='display:flex;justify-content:space-between;color:{TEXT_MUTED};font-size:11px;font-weight:700;'>
                            <span>{rc['source']} · {rc['entity']}</span>
                            <span>{rc['timestamp']}</span>
                        </div>
                        <div style='color:{TEXT_PRIMARY};font-weight:600;margin-top:2px;'>{rc['snippet']}</div>
                    </div>
                    """, unsafe_allow_html=True)

        st.write("")
        b1, b2, _ = st.columns([1, 1.4, 2])
        b1.button("← Back", width="stretch", key=f"bk_{al['id']}",
                  on_click=lambda: ss.update(stage="rca_list"))
        b2.button("See Recommendation", type="primary", width="stretch", key=f"sr_{al['id']}",
                  on_click=lambda: ss.update(stage="recommendation"))

    # ------------------ Step 6 : Executive Recommendation & Decision Brief ------------------
    elif ss["stage"] == "recommendation":
        rec = A["recommendation"]
        header_line()
        
        lead = next((x for x in hyps if x["supported"]), None)
        if lead:
            ltp, lcol = tier_pill(lead["confidence_pct"])
            st.markdown(f"Leading candidate: **{lead['name']}** at <b style='color:{lcol};'>{lead['confidence_pct']}%</b> &nbsp;{ltp}", unsafe_allow_html=True)

        # 1. Action Subheader & Impact
        st.subheader(rec.get("action", "Recommended Action Directive"))
        if rec.get("est_impact_fmt"):
            st.markdown(f"Expected recovery: <b style='font-size:16px;color:{GOOD};'>{rec['est_impact_fmt']} / wk</b> <span style='color:{TEXT_MUTED};font-size:12px;'>({rec.get('basis', '')})</span>", unsafe_allow_html=True)
        else:
            st.caption("Basis: " + str(rec.get("basis", "")))

        # 2. Compact 7-Part Metadata Matrix
        with st.container(border=True):
            rm1, rm2 = st.columns(2)
            with rm1:
                st.markdown(f"<span style='color:{TEXT_MUTED};font-size:11px;font-weight:750;text-transform:uppercase;'>Driver:</span> <span style='font-size:12.5px;font-weight:600;color:{TEXT_PRIMARY};'>{rec.get('driver', 'Identified Root Cause')}</span>", unsafe_allow_html=True)
                st.markdown(f"<span style='color:{TEXT_MUTED};font-size:11px;font-weight:750;text-transform:uppercase;'>Controllable Lever:</span> <span style='font-size:12.5px;font-weight:600;color:{TEXT_PRIMARY};'>{rec.get('lever', 'Operational Lever')}</span>", unsafe_allow_html=True)
                st.markdown(f"<span style='color:{TEXT_MUTED};font-size:11px;font-weight:750;text-transform:uppercase;'>Designated Owner:</span> <span style='font-size:12.5px;font-weight:600;color:{TEXT_PRIMARY};'>{rec.get('owner', 'Category Manager')}</span>", unsafe_allow_html=True)
            with rm2:
                st.markdown(f"<span style='color:{TEXT_MUTED};font-size:11px;font-weight:750;text-transform:uppercase;'>Confidence:</span> <span style='font-size:12.5px;font-weight:600;color:{TEXT_PRIMARY};'>{rec.get('confidence', 'High')}</span>", unsafe_allow_html=True)
                st.markdown(f"<span style='color:{TEXT_MUTED};font-size:11px;font-weight:750;text-transform:uppercase;'>Monitoring Plan:</span> <span style='font-size:12.5px;font-weight:600;color:{TEXT_PRIMARY};'>{rec.get('monitoring_plan', 'Daily telemetry tracking')}</span>", unsafe_allow_html=True)

        # 3. Persona Toggle
        pkey = persona["llm_persona"]
        other_persona = "CXO" if pkey == "Category Manager" else "Category Manager"
        if st.toggle(f"Preview as {other_persona}", key=f"preview_{al['id']}"):
            pkey = other_persona

        # 4. Compact Audited LLM Explanation Box (under 75 words)
        with st.container(border=True):
            st.markdown(pill("LLM EXPLANATION · AUTO-AUDITED", ACCENT_PURPLE_DARK, ACCENT_PURPLE_LIGHT, ACCENT_PURPLE_BORDER, "⚡"), unsafe_allow_html=True)
            
            nkey = (al["id"], pkey)
            if nkey not in ss["narrations"]:
                payload = redact_for_cxo(dict(A)) if pkey == "CXO" else dict(A)
                t0 = time.time()
                text, eng = llm.narrate(payload, pkey)
                t1 = time.time()
                clean, removed, audit = llm.self_verify(text, payload)
                t2 = time.time()
                
                assert isinstance(clean, str), "LLM narrative must be a string"
                normalized_clean = " ".join(clean.split()).strip()
                
                ss["narrations"][nkey] = {
                    "clean": normalized_clean, "removed": removed, "engine": eng,
                    "audit": audit, "narrate_latency": t1 - t0,
                    "verify_latency": t2 - t1
                }
                
            N = ss["narrations"][nkey]
            # Render exactly once without streaming/concatenation
            st.markdown(f"<div style='font-size:13.5px;line-height:1.55;color:{TEXT_PRIMARY};font-weight:500;padding:2px 0 6px;'>{N['clean']}</div>", unsafe_allow_html=True)
                
            audit_pill = pill("✓ all claims verified", GOOD, GOOD_BG, GOOD_BORDER, "✓") \
                if not N["removed"] else \
                pill(f"⚠ {len(N['removed'])} unverified claim(s) removed", WARN, WARN_BG, WARN_BORDER, "!")
                
            st.caption("Generated strictly from the verified JSON above · " + audit_pill, unsafe_allow_html=True)

        # 5. Decision validation form
        reason = st.selectbox(
            "Before you decide — anything off?",
            ["", "Not enough evidence", "Wrong cause identified", "Already resolved", "Other"],
            key=f"fb_{al['id']}"
        )
        if reason == "Other":
            st.text_input("Tell us more", key=f"fbo_{al['id']}")

        st.write("")
        f1, f2, _ = st.columns([1, 1, 2])
        f1.button("Approve", type="primary", width="stretch", key=f"ap_{al['id']}",
                  on_click=make_decider(al["id"], al, route, "approved"))
        f2.button("Reject", width="stretch", key=f"rj_{al['id']}",
                  on_click=make_decider(al["id"], al, route, "rejected"))

        # 6. Evidence Ledger Expander (Deterministic, Evidence Retrieval, LLM Audited)
        st.write("")
        with st.expander("Evidence Ledger & Lineage Audit Trail", expanded=False):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"<span style='color:{ACCENT_PURPLE_DARK};font-weight:700;font-size:12px;'>DETERMINISTIC INFERENCE</span>", unsafe_allow_html=True)
                for line in ["Anomaly detection (|z| ≥ 1.5 & |Δ| ≥ 10%)",
                             "Source reconciliation (grain alignment)",
                             "Change Log lookup (Fast Path)",
                             "Hypothesis testing (4 counterfactuals)",
                             "Weighted evidence formula (W₁–W₄)",
                             "Conflict check (cross-region)",
                             "Access gate (CXO SKU scrub)"]:
                    st.caption("✓ " + line)
            with c2:
                st.markdown(f"<span style='color:{ACCENT_PURPLE_DARK};font-weight:700;font-size:12px;'>MULTI-SOURCE RETRIEVAL</span>", unsafe_allow_html=True)
                st.caption("✓ Multi-source evidence indexing")
                st.caption("✓ Contextual telemetry chunk retrieval")
                st.caption("✓ Provenance & citation binding")
                st.caption("✓ Empirical feedback calibration")
            with c3:
                st.markdown(f"<span style='color:{ACCENT_PURPLE_DARK};font-weight:700;font-size:12px;'>LLM NARRATION (AUDITED)</span>", unsafe_allow_html=True)
                st.caption("✓ Narrative generation (verified JSON)")
                st.caption("✓ Self-verification claim auditor")
                st.caption("✓ Zero numeric hallucination gate")
            st.divider()
            st.caption(f"2 LLM calls · narration {N.get('narrate_latency', 0):.1f}s · "
                       f"verification {N.get('verify_latency', 0):.1f}s · "
                       f"retrieval & deterministic steps ~instant")


if ss["open_aid"]:
    rca_modal()
