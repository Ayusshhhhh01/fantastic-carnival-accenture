"""
CAUSE deterministic engine — Steps 1..7, 10.

HARD RULE enforced here: every number in the output JSON below was computed
by this file. The LLM never sees raw data and never computes anything; it
only receives the finished JSON produced here (see llm.py).
"""
import time
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

Z_THRESHOLD = 1.5
PCT_THRESHOLD = 0.10          # 10%
MIN_BASELINE_WEEKS = 3        # need >= 3 weeks of history for a baseline
SPARSE_FLOOR = 0.50           # completeness hard floor for calling the LLM
CONF_LOW = 0.50
SUPPLY_EXPLAIN_MIN = 0.60     # counterfactual must explain >= 60% of move
DEMAND_SPIKE_MIN = 0.25       # >= 25% spend change counts as a spike
PRICE_MOVE_MIN = 0.05         # >= 5% price change counts as material


# ---------------------------------------------------------------- helpers --
def fmt_inr(x) -> str:
    x = float(x)
    sign = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1e7:
        return f"{sign}\u20b9{x/1e7:.2f}Cr"
    if x >= 1e5:
        return f"{sign}\u20b9{x/1e5:.1f}L"
    return f"{sign}\u20b9{x:,.0f}"


def _clean(obj):
    """numpy -> native for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        return None if (np.isnan(v) or np.isinf(v)) else round(v, 4)
    if isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
        return None
    if isinstance(obj, (pd.Timestamp,)):
        return obj.strftime("%Y-%m-%d")
    return obj


class Ledger:
    """Step 10 evidence ledger: what ran, on which engine, how long, ~cost."""

    def __init__(self):
        self.rows = []

    def add(self, step, engine, t0, note, cost_usd=0.0):
        self.rows.append({
            "step": step,
            "engine": engine,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
            "est_cost_usd": round(cost_usd, 5),
            "note": note,
        })

    def df(self):
        return pd.DataFrame(self.rows)


# ------------------------------------------------------------------ load --
def load_data():
    sales = pd.read_csv(DATA / "sales_daily.csv", parse_dates=["date"])
    camps = pd.read_csv(DATA / "campaigns_weekly.csv", parse_dates=["week_start"])
    inv = pd.read_csv(DATA / "inventory_daily.csv", parse_dates=["date"])
    log = pd.read_csv(DATA / "change_log.csv", parse_dates=["date"])
    return sales, camps, inv, log


# ------------------------------------------- Step 2: reconcile to weekly --
def to_weekly(df, date_col, value_cols, dims):
    """Deterministic resample of a daily source to Monday-labelled weeks."""
    d = df.copy()
    d["week_start"] = d[date_col] - pd.to_timedelta(d[date_col].dt.dayofweek,
                                                    unit="D")
    g = d.groupby(dims + ["week_start"], as_index=False)[value_cols].sum()
    return g


# ------------------------------------------------ Step 1: detect anomalies --
def detect(sales_wk, camp_wk):
    alerts = []
    cur_week = sales_wk.week_start.max()

    # --- KPI 1: Revenue by category x region ---
    cells = sales_wk[["category", "region"]].drop_duplicates()
    for _, r in cells.iterrows():
        s = sales_wk[(sales_wk.category == r.category) &
                     (sales_wk.region == r.region)].sort_values("week_start")
        hist = s[s.week_start < cur_week].tail(4)
        cur_row = s[s.week_start == cur_week]
        if cur_row.empty:
            continue
        cur = float(cur_row.revenue.iloc[0])
        base = float(hist.revenue.mean()) if len(hist) else 0.0
        std = float(hist.revenue.std(ddof=1)) if len(hist) >= 2 else 0.0
        delta = cur - base
        pct = (delta / base) if base else None
        z = ((cur - base) / std) if std else None

        low_data = len(hist) < MIN_BASELINE_WEEKS
        stat_ok = (low_data and abs(delta) > 2e5) or \
                  (z is not None and abs(z) >= Z_THRESHOLD)
        size_ok = pct is None or abs(pct) >= PCT_THRESHOLD
        if not (stat_ok and size_ok):
            continue
        alerts.append({
            "kpi": "Revenue",
            "category": r.category, "region": r.region,
            "week_start": cur_week,
            "current": cur, "baseline_mean": base, "baseline_std": std,
            "baseline_weeks": int(len(hist)),
            "delta_inr": delta, "pct_change": pct, "z_score": z,
            "direction": "down" if delta < 0 else "up",
            "low_data": low_data,
        })

    # --- KPI 2: Marketing spend by category ---
    cats = camp_wk.category.unique()
    for cat in cats:
        s = camp_wk[camp_wk.category == cat].groupby("week_start",
                                                     as_index=False)["spend"].sum()
        hist = s[s.week_start < cur_week].tail(4)
        cur_row = s[s.week_start == cur_week]
        if cur_row.empty or hist.empty:
            continue
        cur = float(cur_row.spend.iloc[0])
        base = float(hist.spend.mean())
        std = float(hist.spend.std(ddof=1)) if len(hist) >= 2 else 0.0
        delta = cur - base
        pct = delta / base if base else None
        z = (cur - base) / std if std else None
        if z is not None and abs(z) >= Z_THRESHOLD and pct is not None \
                and abs(pct) >= PCT_THRESHOLD:
            alerts.append({
                "kpi": "Marketing Spend", "category": cat, "region": "(all)",
                "week_start": cur_week,
                "current": cur, "baseline_mean": base, "baseline_std": std,
                "baseline_weeks": int(len(hist)),
                "delta_inr": delta, "pct_change": pct, "z_score": z,
                "direction": "down" if delta < 0 else "up",
                "low_data": False,
            })

    # sort by absolute rupee impact, not %
    alerts.sort(key=lambda a: abs(a["delta_inr"]), reverse=True)
    for i, a in enumerate(alerts):
        a["id"] = f"A{i+1}"
        a["delta_fmt"] = fmt_inr(a["delta_inr"])
        a["current_fmt"] = fmt_inr(a["current"])
        a["baseline_fmt"] = fmt_inr(a["baseline_mean"])
        a["pct_fmt"] = ("n/a (no baseline)" if a["pct_change"] is None
                        else f"{a['pct_change']*100:+.1f}%")
        a["z_fmt"] = "n/a" if a["z_score"] is None else f"{a['z_score']:.2f}"
    return alerts, cur_week


# ------------------------------------------------------- Step 3: fast path --
def fast_path_check(alert, changelog):
    t0 = time.perf_counter()
    ws, we = alert["week_start"], alert["week_start"] + pd.Timedelta(days=6)
    hits = changelog[
        (changelog.date >= ws - pd.Timedelta(days=2)) &
        (changelog.date <= we + pd.Timedelta(days=2)) &
        (changelog.category == alert["category"]) &
        (changelog.region == alert["region"])]
    result = None
    if len(hits):
        h = hits.iloc[0]
        result = {
            "matched": True,
            "event_date": str(h["date"].date()),
            "event_type": h["event_type"],
            "description": h["description"],
            "window": f"[{ws.date()} .. {we.date()}] +/- 2 days",
        }
    return result, t0


# ------------------------------- Step 4: deep path — competing hypotheses --
def hypothesis_supply(alert, sales_wk_daily, sales, inv):
    """Counterfactual: pre-stockout daily rate projected across stockout days."""
    cat, reg = alert["category"], alert["region"]
    wk = alert["week_start"]
    we = wk + pd.Timedelta(days=6)

    # every product in this cell that stocked out during the alert week,
    # ranked by pre-period revenue exposure (not just the cell's top seller)
    so_week = inv[(inv.region == reg) & (inv.stock_out_flag == 1) &
                  (inv.date >= wk) & (inv.date <= we)]
    so_week = so_week[so_week.product_id.isin(
        sales[(sales.category == cat)].product_id.unique())]
    candidates = []
    for pid in so_week.product_id.unique():
        pre = sales[(sales.product_id == pid) & (sales.region == reg) &
                    (sales.date < wk) & (sales.date >= wk - pd.Timedelta(days=28))]
        if len(pre):
            candidates.append((pid, float(pre.revenue.mean()), len(pre)))
    candidates.sort(key=lambda t: t[1] * t[2], reverse=True)

    if not candidates:
        return {
            "name": "Supply-side (stock-out)",
            "supported": False,
            "deciding_metric": "stock-out days in window",
            "deciding_value": ("0 stock-out day(s) for any product in this "
                               f"{cat}/{reg} cell during the alert week"),
            "data_source": "inventory_daily.csv (stock_out_flag)",
            "verdict": ("REJECTED - no stock-out exposure exists in this "
                        "cell during the window"),
            "score": 0.0,
            "detail": {},
        }

    pid, pre_rate, n_pre = candidates[0]
    pname = sales[sales.product_id == pid].product_name.iloc[0]
    completeness = n_pre / 28.0

    days = sorted(pd.to_datetime(
        so_week[so_week.product_id == pid].date).unique())

    w0, w1 = days[0], days[-1]
    actual = float(sales[(sales.product_id == pid) & (sales.region == reg) &
                         (sales.date >= w0) & (sales.date <= w1)]
                   .revenue.sum())
    counterfactual = pre_rate * len(days)
    gap = counterfactual - actual
    total_move = abs(alert["delta_inr"])
    explain_ratio = gap / total_move if total_move else 0.0
    supported = explain_ratio >= SUPPLY_EXPLAIN_MIN

    return {
        "name": "Supply-side (stock-out)",
        "supported": bool(supported),
        "deciding_metric": "counterfactual gap / total KPI move",
        "deciding_value": (
            f"Pre-stockout daily avg {fmt_inr(pre_rate)} x "
            f"{len(days)} stock-out days = {fmt_inr(counterfactual)} "
            f"expected vs {fmt_inr(actual)} actual -> unexplained loss "
            f"{fmt_inr(gap)}, which is {explain_ratio*100:.0f}% of the "
            f"{fmt_inr(total_move)} KPI move"),
        "data_source": f"inventory_daily.csv (flag=1 {w0.date()}..{w1.date()})"
                       f" + sales_daily.csv ({pid})",
        "verdict": ("SUPPORTED" if supported else
                    f"REJECTED - counterfactual gap accounts for "
                    f"{explain_ratio*100:.0f}% of the move, and the move's "
                    f"direction ({alert['direction']}) contradicts a "
                    f"stock-out loss explanation"
                    if explain_ratio < 0 else
                    f"REJECTED - counterfactual explains only "
                    f"{explain_ratio*100:.0f}% of the move (needs >= "
                    f"{SUPPLY_EXPLAIN_MIN*100:.0f}%)"),
        "score": round(min(max(explain_ratio, 0.0), 1.0), 3),
        "detail": {
            "product_id": pid, "product_name": pname,
            "stockout_days": [str(d.date()) for d in days],
            "pre_rate_daily": pre_rate,
            "pre_rate_daily_fmt": fmt_inr(pre_rate),
            "counterfactual_revenue": counterfactual,
            "counterfactual_fmt": fmt_inr(counterfactual),
            "actual_revenue_window": actual,
            "actual_fmt": fmt_inr(actual),
            "unexplained_gap": gap,
            "gap_fmt": fmt_inr(gap),
            "explains_pct": round(explain_ratio * 100, 1),
            "history_completeness": round(completeness, 3),
        },
    }


def hypothesis_demand(alert, camps_wk_cell):
    """Check for a campaign/demand spike in the same window."""
    cur = camps_wk_cell[camps_wk_cell.week_start == alert["week_start"]]
    hist = camps_wk_cell[camps_wk_cell.week_start < alert["week_start"]].tail(4)
    cur_spend = float(cur.spend.sum()) if len(cur) else 0.0
    base_spend = float(hist.spend.mean()) if len(hist) else 0.0
    ratio = (cur_spend - base_spend) / base_spend if base_spend else None

    moved_down = alert["direction"] == "down"
    # a demand-side explanation requires spend moving WITH the KPI
    aligned = (ratio is not None and
               ((ratio >= DEMAND_SPIKE_MIN and not moved_down) or
                (ratio <= -DEMAND_SPIKE_MIN and moved_down)))
    supported = bool(aligned)

    rv = "n/a" if ratio is None else f"{ratio*100:+.1f}%"
    verdict = ("SUPPORTED" if supported else
               f"REJECTED - spend changed {rv} vs baseline "
               f"{fmt_inr(base_spend)} (needs a >={DEMAND_SPIKE_MIN*100:.0f}% "
               f"move aligned with the KPI direction)")
    return {
        "name": "Demand-side (campaign/demand shift)",
        "supported": supported,
        "deciding_metric": "campaign spend change vs trailing 4-wk baseline",
        "deciding_value": (f"{fmt_inr(cur_spend)} this week vs "
                           f"{fmt_inr(base_spend)} baseline -> {rv}"),
        "data_source": "campaigns_weekly.csv (same category x region)",
        "verdict": verdict,
        "score": round(min(abs(ratio) / 0.5, 1.0) if ratio is not None else 0.0, 3),
        "detail": {
            "spend_current": cur_spend, "spend_baseline": base_spend,
            "spend_change_pct": None if ratio is None else round(ratio * 100, 1),
        },
    }


def hypothesis_pricing(alert, sales):
    cat, reg = alert["category"], alert["region"]
    wk = alert["week_start"]
    cur = sales[(sales.category == cat) & (sales.region == reg) &
                (sales.date >= wk) & (sales.date < wk + pd.Timedelta(days=7))]
    pre = sales[(sales.category == cat) & (sales.region == reg) &
                (sales.date < wk) & (sales.date >= wk - pd.Timedelta(days=28))]
    if cur.empty or pre.empty:
        return {"name": "Pricing change", "supported": False,
                "deciding_metric": "unit_price delta",
                "deciding_value": "insufficient rows",
                "data_source": "sales_daily.csv", "verdict": "REJECTED",
                "score": 0.0, "detail": {}}
    max_delta = 0.0
    worst_pid = None
    for pid, grp in cur.groupby("product_id"):
        p_now = grp.unit_price.max()
        p_pre = pre[pre.product_id == pid].unit_price.max()
        if p_pre:
            d = abs(p_now - p_pre) / p_pre
            if d > max_delta:
                max_delta, worst_pid = d, pid
    supported = max_delta >= PRICE_MOVE_MIN
    dv = (f"max unit_price change {max_delta*100:.2f}%"
          + (f" (product {worst_pid})" if worst_pid else "")
          + f"; threshold {PRICE_MOVE_MIN*100:.0f}%")
    return {
        "name": "Pricing change",
        "supported": bool(supported),
        "deciding_metric": "max unit_price change in window",
        "deciding_value": dv,
        "data_source": "sales_daily.csv unit_price column",
        "verdict": ("SUPPORTED" if supported else
                    f"REJECTED - largest price move was only "
                    f"{max_delta*100:.2f}%"),
        "score": round(min(max_delta / PRICE_MOVE_MIN, 1.0), 3),
        "detail": {"max_price_delta_pct": round(max_delta * 100, 2)},
    }


# --------------------------------------------- Step 5: confidence scoring --
# Per-candidate weight profiles: each hypothesis type emphasises different
# evidence factors. Confidence% = 100 * Σ(Wi · factor_i).
FACTOR_LABELS = {
    "temporal_correlation": ("W\u2081", "Temporal Correlation"),
    "source_agreement": ("W\u2082", "Source Reliability"),
    "hypothesis_margin": ("W\u2083", "Contrary Stats Score"),
    "data_completeness": ("W\u2084", "Evidence Density"),
}
HYP_WEIGHTS = {
    "Supply": {"temporal_correlation": 0.35, "source_agreement": 0.20,
               "hypothesis_margin": 0.15, "data_completeness": 0.30},
    "Demand": {"temporal_correlation": 0.10, "source_agreement": 0.45,
               "hypothesis_margin": 0.20, "data_completeness": 0.25},
    "Pricing": {"temporal_correlation": 0.30, "source_agreement": 0.15,
                "hypothesis_margin": 0.35, "data_completeness": 0.20},
}


def attach_hypothesis_confidence(hyps, comps):
    """Give every hypothesis its own weighted confidence percentage.

    Factors are hypothesis-specific where they should be:
      - Source Reliability = do independent data sources back THIS candidate
        (a rejected candidate has sources contradicting it)
      - Contrary Stats Score = how decisively this candidate beats the
        strongest competing candidate on raw metric strength
    """
    scores = [h["score"] for h in hyps]
    for i, h in enumerate(hyps):
        kind = h["name"].split("-")[0].split(" ")[0]
        w = HYP_WEIGHTS.get(kind, HYP_WEIGHTS["Supply"])
        others = [s for j, s in enumerate(scores) if j != i]
        margin = max(0.0, h["score"] - max(others)) if others else h["score"]
        src = comps["source_agreement"] if h["supported"] \
            else round(comps["source_agreement"] * h["score"], 3)
        f = {
            "temporal_correlation": comps["temporal_correlation"],
            "source_agreement": src,
            "hypothesis_margin": round(margin, 3),
            "data_completeness": comps["data_completeness"],
        }
        pct = sum(w[k] * f[k] for k in w)
        h["confidence_pct"] = round(pct * 100)
        h["weights"] = w
        h["factors"] = f



def score_confidence(alert, hyps, winner):
    components = {}
    detail = winner.get("detail", {})

    # 1. temporal correlation
    so_days = detail.get("stockout_days", [])
    if so_days:
        wk = alert["week_start"]
        inside = sum(1 for d in so_days
                     if pd.Timestamp(d) >= wk and
                     pd.Timestamp(d) <= wk + pd.Timedelta(days=6))
        components["temporal_correlation"] = round(
            (inside / max(len(so_days), 1)) *
            min(abs(alert["z_score"]) / Z_THRESHOLD, 1.0)
            if alert["z_score"] else inside / max(len(so_days), 1), 3)
    else:
        components["temporal_correlation"] = round(
            min(abs(alert["z_score"]) / 2.5, 1.0) if alert["z_score"] else 0.3, 3)

    # 2. source agreement
    agree = 0
    sources = 0
    if so_days:
        sources += 1
        agree += 1 if winner["supported"] else 0   # inventory agrees w/ sales
    sources += 1                                    # sales decomposition
    agree += 1 if winner["supported"] else 0
    if winner["name"].startswith("Demand"):
        sources += 1
        agree += 1 if winner["supported"] else 0
    components["source_agreement"] = round(agree / sources, 3)

    # 3. data completeness (real sparsity penalty)
    comp = detail.get("history_completeness")
    if comp is None:
        comp = min(alert["baseline_weeks"] / 4.0, 1.0)
    components["data_completeness"] = round(comp, 3)

    # 4. hypothesis margin
    ranked = sorted((h["score"] for h in hyps), reverse=True)
    top = ranked[0] if ranked else 0.0
    second = ranked[1] if len(ranked) > 1 else 0.0
    components["hypothesis_margin"] = round(top - second, 3)

    weights = {"temporal_correlation": 0.30, "source_agreement": 0.25,
               "data_completeness": 0.25, "hypothesis_margin": 0.20}
    score = sum(components[k] * w for k, w in weights.items())
    tier = "High" if score > 0.75 else ("Medium" if score >= CONF_LOW else "Low")

    gaps = []
    if comp < SPARSE_FLOOR:
        gaps.append(f"data completeness {comp*100:.0f}% for the affected "
                    f"product (hard floor {SPARSE_FLOOR*100:.0f}%; "
                    f"only {int(round(comp*28))} of 28 baseline days present)")
    if alert.get("baseline_weeks", 0) < MIN_BASELINE_WEEKS:
        gaps.append(f"only {alert['baseline_weeks']} baseline week(s) of KPI "
                    f"history (need >= {MIN_BASELINE_WEEKS})")
    if score < CONF_LOW:
        gaps.append(f"composite confidence {score:.2f} below Low tier "
                    f"cutoff {CONF_LOW:.2f}")
    return {"score": round(score, 3), "tier": tier,
            "components": components, "gaps": gaps}


# ------------------------------------------------- Step 6: conflict check --
def conflict_check(alert, sales_wk, inv, sales, winner, camps_wk=None):
    """
    Compare the winning story against comparable cells with similar exposure.

    A divergence is only a CONFLICT when it is itself unexplained: if the
    sibling's opposite outcome is accounted for by its own verified factor
    (e.g. a campaign spike), the winning story stands. If the divergence has
    no quantified explanation, the evidence contradicts itself -> unresolved.
    """
    if alert["kpi"] != "Revenue":
        return {"conflict": False, "comparable_cells": [],
                "note": "Aggregate KPI - cross-region exposure comparison "
                        "not applicable."}
    wk = alert["week_start"]
    we = wk + pd.Timedelta(days=6)
    cat = alert["category"]

    siblings = []
    for reg in [r for r in sales_wk.region.unique() if r != alert["region"]]:
        so = inv[(inv.region == reg) & (inv.stock_out_flag == 1) &
                 (inv.date >= wk) & (inv.date <= we)]
        so = so[so.product_id.isin(
            sales[(sales.category == cat)].product_id.unique())]
        if so.empty:
            continue
        days_per_prod = so.groupby("product_id").date.nunique()
        pid = days_per_prod.idxmax()
        if days_per_prod[pid] < 2:
            continue
        sib = sales_wk[(sales_wk.category == cat) & (sales_wk.region == reg)]
        hist = sib[sib.week_start < wk].tail(4)
        cur_r = sib[sib.week_start == wk]
        if cur_r.empty or hist.empty:
            continue
        pct = (float(cur_r.revenue.iloc[0]) / float(hist.revenue.mean())) - 1

        entry = {"region": reg, "product_id": pid,
                 "stockout_days": int(days_per_prod[pid]),
                 "revenue_pct_change": round(pct * 100, 1)}

        # is this sibling's divergent outcome explained by its own campaign?
        if camps_wk is not None:
            c_cur = camps_wk[(camps_wk.category == cat) & (camps_wk.region == reg)
                             & (camps_wk.week_start == wk)]
            c_hist = camps_wk[(camps_wk.category == cat) & (camps_wk.region == reg)
                              & (camps_wk.week_start < wk)].tail(4)
            if len(c_cur) and len(c_hist) and float(c_hist.spend.mean()):
                sp = float(c_cur.spend.sum()) / float(c_hist.spend.mean()) - 1
                entry["campaign_spend_change_pct"] = round(sp * 100, 1)
                entry["divergence_explained_by_campaign"] = \
                    sp >= DEMAND_SPIKE_MIN
        siblings.append(entry)

    for s in siblings:
        divergent = (alert["delta_inr"] < 0 and
                     s["revenue_pct_change"] > -3) or \
                    (alert["delta_inr"] > 0 and
                     s["revenue_pct_change"] < 3)
        if not divergent:
            continue
        if s.get("divergence_explained_by_campaign"):
            return {"conflict": False, "comparable_cells": siblings,
                    "note": (f"{s['region']} shows the same stock-out "
                             f"exposure with an opposite revenue outcome "
                             f"({s['revenue_pct_change']:+.1f}%), but its "
                             f"own campaign spend rose "
                             f"{s['campaign_spend_change_pct']:+.1f}% - "
                             f"the divergence is explained, so the winning "
                             f"hypothesis stands.")}
        return {
            "conflict": True,
            "signal_a": (f"{alert['category']}/{alert['region']}: stock-out "
                         f"exposure coincided with {alert['pct_fmt']} "
                         f"revenue ({alert['delta_fmt']})"),
            "signal_b": (f"{alert['category']}/{s['region']}: similar "
                         f"stock-out ({s['stockout_days']} days, product "
                         f"{s['product_id']}) yet revenue moved "
                         f"{s['revenue_pct_change']:+.1f}% with no "
                         f"quantified offsetting factor"),
            "comparable_cells": siblings,
        }
    return {"conflict": False, "comparable_cells": siblings}


# ------------------------------------------- Step 7: access gate (CXO) ----
CXO_REDACTED_KEYS = {"product_id", "product_name", "stockout_days"}
ID_PATTERN = None  # compiled lazily
CXO_LOG = []


def redact_for_cxo(payload):
    import re
    # collect sensitive literal values (names, ids) so they can also be
    # scrubbed from free-text fields like verdicts and data sources
    sensitive = set()

    def collect(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in CXO_REDACTED_KEYS and isinstance(v, str):
                    sensitive.add(v)
                collect(v)
        elif isinstance(o, list):
            for v in o:
                collect(v)
    collect(payload)

    def scrub(s: str) -> str:
        for tok in sensitive:
            s = s.replace(tok, "[redacted SKU]")
            parts = tok.split()
            for p in parts:
                if len(p) > 3:
                    s = s.replace(p, "[redacted]")
        s = re.sub(r"\b[A-Z]{1,2}\d{3}\b", "[redacted SKU]", s)
        return s

    def strip(o):
        if isinstance(o, dict):
            return {k: (None if k in CXO_REDACTED_KEYS else strip(v))
                    for k, v in o.items()}
        if isinstance(o, list):
            return [strip(v) for v in o]
        if isinstance(o, str):
            return scrub(o)
        return o

    CXO_LOG.append("Access check: CXO role -> SKU/product-level fields "
                   "redacted (category aggregates only).")
    return strip(payload)


# ------------------------------------------------------ Step 10: recommend --
def recommend(alert, winner, conflict, abstained):
    if abstained or winner is None:
        return {
            "action": "Collect more data before acting - do not treat this "
                      "anomaly as explained.",
            "est_impact": None, "est_impact_fmt": None,
            "basis": "Insufficient history; no counterfactual can be computed.",
        }
    if conflict.get("conflict"):
        return {
            "action": "Escalate for manual review: the leading explanation "
                      "does not replicate across comparable regions.",
            "est_impact": None, "est_impact_fmt": None,
            "basis": "Conflicting regional evidence (see conflict panel).",
        }
    d = winner.get("detail", {})
    if winner["supported"] and winner["name"].startswith("Supply"):
        daily = d.get("pre_rate_daily", 0)
        return {
            "action": (f"Expedite replenishment of {d.get('product_name')} in "
                       f"{alert['region']} (transfer stock from sibling DCs); "
                       f"each recovered day is worth ~{fmt_inr(daily)} at the "
                       f"pre-stockout run rate."),
            "est_impact": daily * 7,
            "est_impact_fmt": fmt_inr(daily * 7),
            "basis": f"Pre-stockout daily average {fmt_inr(daily)} x 7 days.",
        }
    if winner["supported"] and winner["name"].startswith("Demand"):
        d2 = winner.get("detail", {})
        return {
            "action": (f"Maintain/scale the campaign mix in "
                       f"{alert['category']}/{alert['region']}; it coincides "
                       f"with {alert['pct_fmt']} revenue."),
            "est_impact": alert["delta_inr"],
            "est_impact_fmt": alert["delta_fmt"],
            "basis": f"Week revenue delta {alert['delta_fmt']} vs baseline.",
        }
    return {
        "action": "Monitor for one more cycle; no single hypothesis cleared "
                  "the falsification bar.",
        "est_impact": None, "est_impact_fmt": None,
        "basis": "All hypotheses scored below support thresholds.",
    }


# ------------------------------------------------------------ full runner --
def analyze_alert(alert, sales, camps_wk, sales_wk, inv, changelog, ledger):
    payload = {"alert": alert}

    # Step 2 reconciliation is logged once globally (see run()); per-alert trail:
    payload["reconcile_log"] = [
        "Resampled daily sales to weekly grain (Mon-Sun) to align with "
        "campaign cadence before any comparison.",
        "Aligned inventory_daily.csv to the same week windows for "
        "stock-out lookups.",
    ]

    # Step 3 fast path
    fp, t0 = fast_path_check(alert, changelog)
    aid = f"[{alert['id']}]"
    ledger.add(f"Step 3 Fast Path {aid}", "Deterministic", t0,
               "Direct event match found" if fp else "No logged event matched")
    payload["fast_path"] = fp

    if fp:
        payload["route"] = "FAST_PATH"
        payload["hypotheses"] = []
        payload["confidence"] = {
            "score": 0.95, "tier": "High",
            "components": {"temporal_correlation": 1.0,
                           "source_agreement": 1.0,
                           "data_completeness": 1.0,
                           "hypothesis_margin": 0.8},
            "gaps": []}
        payload["conflict"] = conflict_check(alert, sales_wk, inv, sales,
                                             None, camps_wk)
        payload["recommendation"] = {
            "action": (f"Treat as operationally explained by the logged "
                       f"[{fp['event_type']}] on {fp['event_date']}; verify "
                       f"recovery after the incident window closes."),
            "est_impact": None, "est_impact_fmt": None,
            "basis": f"Direct change-log match inside {fp['window']}.",
        }
        return payload

    # Step 4 deep path
    t0 = time.perf_counter()
    camps_cell = camps_wk[(camps_wk.category == alert["category"])] if \
        alert["region"] == "(all)" else \
        camps_wk[(camps_wk.category == alert["category"]) &
                 (camps_wk.region == alert["region"])]
    hyps = [
        hypothesis_supply(alert, None, sales, inv),
        hypothesis_demand(alert, camps_cell),
        hypothesis_pricing(alert, sales),
    ]
    hyps = [h for h in hyps if h]
    ledger.add(f"Step 4 Hypothesis tests (x3, falsified) {aid}", "Deterministic", t0,
               "; ".join(f"{h['name'].split(' ')[0]}:"
                         f"{'SUPPORTED' if h['supported'] else 'rejected'}"
                         for h in hyps))
    payload["hypotheses"] = hyps

    ranked = sorted(hyps, key=lambda h: (h["supported"], h["score"]),
                    reverse=True)
    winner = ranked[0]

    # Step 5 confidence
    t0 = time.perf_counter()
    conf = score_confidence(alert, hyps, winner)
    attach_hypothesis_confidence(hyps, conf["components"])
    ledger.add(f"Step 5 Confidence scoring {aid}", "Deterministic", t0,
               f"score={conf['score']}, tier={conf['tier']}")
    payload["confidence"] = conf

    abstain = conf["tier"] == "Low" or \
        conf["components"]["data_completeness"] < SPARSE_FLOOR

    if abstain:
        payload["route"] = "ABSTAIN"
        missing = "; ".join(conf["gaps"]) if conf["gaps"] else \
            "composite confidence below floor"
        days_short = max(0, 28 - int(round(
            conf["components"]["data_completeness"] * 28)))
        payload["abstention"] = {
            "message": f"Insufficient evidence. Missing: {missing}. "
                       f"Recommend: collect {days_short} more day(s) of "
                       f"sales/inventory history for this cell before "
                       f"re-running analysis.",
        }
        payload["recommendation"] = recommend(alert, winner,
                                              {"conflict": False}, True)
        return payload

    # Step 6 conflict check
    t0 = time.perf_counter()
    conflict = conflict_check(alert, sales_wk, inv, sales, winner, camps_wk)
    ledger.add(f"Step 6 Conflict check (cross-region) {aid}", "Deterministic", t0,
               "CONFLICT detected" if conflict["conflict"] else
               "no contradiction found")
    payload["conflict"] = conflict
    payload["route"] = "UNRESOLVED_CONFLICT" if conflict["conflict"] \
        else "RESOLVED"

    payload["recommendation"] = recommend(alert, winner, conflict, False)
    return payload


def run():
    ledger = Ledger()
    CXO_LOG.clear()

    t0 = time.perf_counter()
    sales, camps, inv, changelog = load_data()

    # ---- Step 2: explicit reconciliation ----
    sales_wk = to_weekly(sales, "date", ["units_sold", "revenue"],
                         ["category", "region"])
    camps_wk = camps.copy()  # already weekly
    ledger.add("Step 2 Reconcile grains", "Deterministic", t0,
               "Resampled daily sales to weekly grain to align with campaign "
               "cadence (91 daily rows/cell -> 13 Mondays); campaign table "
               "already weekly.")

    t0 = time.perf_counter()
    alerts, cur_week = detect(sales_wk, camps_wk)
    ledger.add("Step 1 Detect anomalies", "Deterministic", t0,
               f"{len(alerts)} material alerts (threshold: |z|>=1.5 AND "
               f"|delta|>=10%), sorted by rupee impact")

    results = []
    for a in alerts:
        payload = analyze_alert(a, sales, camps_wk, sales_wk, inv,
                                changelog, ledger)
        results.append(payload)

    return {"alerts": [_clean(r) for r in results],
            "ledger_rows": ledger.rows,
            "cxo_access_log": CXO_LOG,
            "cur_week": str(cur_week.date())}
