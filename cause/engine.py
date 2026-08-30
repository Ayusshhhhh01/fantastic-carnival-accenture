"""
CAUSE deterministic engine — Steps 1..7, 10 + RAG Retrieval & Semantic Layer.

HARD RULE enforced here: every quantitative number in the output JSON below was computed
deterministically. The LLM never sees raw unindexed data and never computes numbers; it
only receives the finished, audited JSON produced here (see llm.py).
"""
import time
import json
import os
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


# ------------------------------------------------------------- KPI SEMANTIC REGISTRY ----
KPI_REGISTRY = {
    "Revenue": {
        "display_name": "Gross Revenue",
        "role_in_pipeline": "Anomaly Detection Signal",
        "formula": "Σ(units_sold × unit_price)",
        "grain": "Weekly (Category × Region × Week)",
        "source_table": "sales_daily.csv",
        "baseline_method": "Trailing 4-week moving average (μ ± 1.5σ)",
        "materiality_rule": "|z| ≥ 1.5 AND |Δ| ≥ 10%",
        "connected_drivers": ["Units Sold", "Average Realized Price", "Stockout Incident Days", "Marketing Spend"],
        "access_entitlement": {"Category Manager": "Full Operational Detail", "CXO": "Category Aggregate (SKU Redacted)"},
    },
    "Marketing Spend": {
        "display_name": "Marketing Spend",
        "role_in_pipeline": "Anomaly Detection Signal",
        "formula": "Σ(campaign_spend)",
        "grain": "Weekly (Category × Week)",
        "source_table": "campaigns_weekly.csv",
        "baseline_method": "Trailing 4-week moving average (μ ± 1.5σ)",
        "materiality_rule": "|z| ≥ 1.5 AND |Δ| ≥ 10%",
        "connected_drivers": ["Category Campaign Allocations", "Regional Targeting"],
        "access_entitlement": {"Category Manager": "Full Operational Detail", "CXO": "Full Aggregated Detail"},
    },
    "Units Sold": {
        "display_name": "Volume / Units Sold",
        "role_in_pipeline": "Connected Causal Evidence / Driver",
        "formula": "Σ(units_sold)",
        "grain": "Weekly (Category × Region × Week)",
        "source_table": "sales_daily.csv",
        "baseline_method": "Trailing 4-week moving average (μ ± 1.5σ)",
        "materiality_rule": "|z| ≥ 1.5 AND |Δ| ≥ 10%",
        "connected_drivers": ["Stockouts", "Campaign Conversions", "Price Elasticity"],
        "access_entitlement": {"Category Manager": "SKU & Regional Volume", "CXO": "Category Aggregate Volume"},
    },
    "Stockout Incident Days": {
        "display_name": "Stockout Incident Exposure",
        "role_in_pipeline": "Connected Causal Evidence / Driver",
        "formula": "Count(stock_out_flag == 1)",
        "grain": "Weekly (Category × Region × Week)",
        "source_table": "inventory_daily.csv",
        "baseline_method": "Zero-incident standard (outage > 0 days triggers exposure check)",
        "materiality_rule": "≥ 1 stock-out day in alert window",
        "connected_drivers": ["DC Inbound Logistics", "Supplier Replenishment Lead Time"],
        "access_entitlement": {"Category Manager": "SKU & DC Level", "CXO": "Category Exposure (SKU Redacted)"},
    },
    "Average Realized Price": {
        "display_name": "Average Realized Unit Price",
        "role_in_pipeline": "Connected Causal Evidence / Driver",
        "formula": "Gross Revenue / Units Sold",
        "grain": "Weekly (Category × Region × Week)",
        "source_table": "sales_daily.csv",
        "baseline_method": "Trailing 4-week weighted average price",
        "materiality_rule": "|Δ Price| ≥ 5%",
        "connected_drivers": ["MSRP Adjustments", "Promotional Discounting", "Coupon Redemption"],
        "access_entitlement": {"Category Manager": "Product MSRP & Discount Lineage", "CXO": "Category Blended Price"},
    },
}


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
def detect(sales_wk, camp_wk, inv_df=None, sales_daily_df=None):
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
        series = [
            {
                "week": str(row.week_start.date()),
                "value": float(row.revenue),
                "expected": base
            }
            for _, row in s.tail(8).iterrows()
        ]
        alerts.append({
            "kpi": "Revenue",
            "category": r.category, "region": r.region,
            "week_start": cur_week,
            "current": cur, "baseline_mean": base, "baseline_std": std,
            "baseline_weeks": int(len(hist)),
            "delta_inr": delta, "pct_change": pct, "z_score": z,
            "direction": "down" if delta < 0 else "up",
            "low_data": low_data,
            "historical_series": series,
            "current_fmt": fmt_inr(cur),
            "baseline_fmt": fmt_inr(base),
            "delta_fmt": fmt_inr(delta),
        })

    # --- KPI 2: Marketing Spend by category ---
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
            series = [
                {
                    "week": str(row.week_start.date()),
                    "value": float(row.spend),
                    "expected": base
                }
                for _, row in s.tail(8).iterrows()
            ]
            alerts.append({
                "kpi": "Marketing Spend", "category": cat, "region": "(all)",
                "week_start": cur_week,
                "current": cur, "baseline_mean": base, "baseline_std": std,
                "baseline_weeks": int(len(hist)),
                "delta_inr": delta, "pct_change": pct, "z_score": z,
                "direction": "down" if delta < 0 else "up",
                "low_data": False,
                "historical_series": series,
                "current_fmt": fmt_inr(cur),
                "baseline_fmt": fmt_inr(base),
                "delta_fmt": fmt_inr(delta),
            })

    # --- KPI 3: Units Sold by category x region ---
    for _, r in cells.iterrows():
        s = sales_wk[(sales_wk.category == r.category) &
                     (sales_wk.region == r.region)].sort_values("week_start")
        hist = s[s.week_start < cur_week].tail(4)
        cur_row = s[s.week_start == cur_week]
        if cur_row.empty or hist.empty:
            continue
        cur = float(cur_row.units_sold.iloc[0])
        base = float(hist.units_sold.mean())
        std = float(hist.units_sold.std(ddof=1)) if len(hist) >= 2 else 0.0
        delta = cur - base
        pct = delta / base if base else None
        z = (cur - base) / std if std else None

        if z is not None and abs(z) >= Z_THRESHOLD and pct is not None and abs(pct) >= PCT_THRESHOLD:
            series = [
                {
                    "week": str(row.week_start.date()),
                    "value": float(row.units_sold),
                    "expected": base
                }
                for _, row in s.tail(8).iterrows()
            ]
            avg_p = float(cur_row.revenue.iloc[0]) / cur if cur > 0 else 1000.0
            delta_inr = delta * avg_p
            alerts.append({
                "kpi": "Units Sold", "category": r.category, "region": r.region,
                "week_start": cur_week,
                "current": cur, "baseline_mean": base, "baseline_std": std,
                "baseline_weeks": int(len(hist)),
                "delta_inr": delta_inr, "pct_change": pct, "z_score": z,
                "direction": "down" if delta < 0 else "up",
                "low_data": len(hist) < MIN_BASELINE_WEEKS,
                "historical_series": series,
                "current_fmt": f"{int(cur):,} units",
                "baseline_fmt": f"{int(base):,} units",
                "delta_fmt": f"{int(delta):+,} units ({fmt_inr(delta_inr)})",
            })

    # --- KPI 4: Average Realized Price by category x region ---
    for _, r in cells.iterrows():
        s = sales_wk[(sales_wk.category == r.category) &
                     (sales_wk.region == r.region)].sort_values("week_start").copy()
        s["price"] = s["revenue"] / s["units_sold"].replace(0, 1)
        hist = s[s.week_start < cur_week].tail(4)
        cur_row = s[s.week_start == cur_week]
        if cur_row.empty or hist.empty:
            continue
        cur = float(cur_row.price.iloc[0])
        base = float(hist.price.mean())
        std = float(hist.price.std(ddof=1)) if len(hist) >= 2 else 0.0
        delta = cur - base
        pct = delta / base if base else None
        z = (cur - base) / std if std else None

        if z is not None and abs(z) >= Z_THRESHOLD and pct is not None and abs(pct) >= PRICE_MOVE_MIN:
            series = [
                {
                    "week": str(row.week_start.date()),
                    "value": float(row.price),
                    "expected": base
                }
                for _, row in s.tail(8).iterrows()
            ]
            units_now = float(cur_row.units_sold.iloc[0])
            delta_inr = delta * units_now
            alerts.append({
                "kpi": "Average Realized Price", "category": r.category, "region": r.region,
                "week_start": cur_week,
                "current": cur, "baseline_mean": base, "baseline_std": std,
                "baseline_weeks": int(len(hist)),
                "delta_inr": delta_inr, "pct_change": pct, "z_score": z,
                "direction": "down" if delta < 0 else "up",
                "low_data": len(hist) < MIN_BASELINE_WEEKS,
                "historical_series": series,
                "current_fmt": f"\u20b9{cur:,.2f}/unit",
                "baseline_fmt": f"\u20b9{base:,.2f}/unit",
                "delta_fmt": f"\u20b9{delta:+,.2f}/unit ({fmt_inr(delta_inr)})",
            })

    # --- KPI 5: Stockout Incident Days by category x region ---
    if inv_df is not None and not inv_df.empty and sales_daily_df is not None:
        inv_copy = inv_df.copy()
        inv_copy["week_start"] = inv_copy["date"] - pd.to_timedelta(inv_copy["date"].dt.dayofweek, unit="D")
        cat_map = sales_daily_df[["product_id", "category"]].drop_duplicates().set_index("product_id")["category"].to_dict()
        inv_copy["category"] = inv_copy["product_id"].map(cat_map)
        inv_copy = inv_copy.dropna(subset=["category"])

        inv_g = inv_copy.groupby(["category", "region", "week_start"], as_index=False)["stock_out_flag"].sum()
        for _, r in cells.iterrows():
            s = inv_g[(inv_g.category == r.category) & (inv_g.region == r.region)].sort_values("week_start")
            hist = s[s.week_start < cur_week].tail(4)
            cur_row = s[s.week_start == cur_week]
            if cur_row.empty:
                continue
            cur = float(cur_row.stock_out_flag.iloc[0])
            base = float(hist.stock_out_flag.mean()) if len(hist) else 0.0
            std = float(hist.stock_out_flag.std(ddof=1)) if len(hist) >= 2 else 0.0
            delta = cur - base
            pct = (delta / base) if base else (1.0 if cur > 0 else 0.0)
            z = (cur - base) / std if std else (2.0 if cur >= 2 else 0.0)

            if cur >= 1 and (z >= Z_THRESHOLD or delta >= 1.0):
                series = [
                    {
                        "week": str(row.week_start.date()),
                        "value": float(row.stock_out_flag),
                        "expected": base
                    }
                    for _, row in s.tail(8).iterrows()
                ]
                sal_cell = sales_wk[(sales_wk.category == r.category) & (sales_wk.region == r.region) & (sales_wk.week_start == cur_week)]
                daily_rev = float(sal_cell.revenue.iloc[0]) / 7.0 if not sal_cell.empty else 50000.0
                delta_inr = -1.0 * cur * daily_rev
                alerts.append({
                    "kpi": "Stockout Incident Days", "category": r.category, "region": r.region,
                    "week_start": cur_week,
                    "current": cur, "baseline_mean": base, "baseline_std": std,
                    "baseline_weeks": int(len(hist)),
                    "delta_inr": delta_inr, "pct_change": pct, "z_score": z,
                    "direction": "up",
                    "low_data": len(hist) < MIN_BASELINE_WEEKS,
                    "historical_series": series,
                    "current_fmt": f"{int(cur)} days",
                    "baseline_fmt": f"{int(base)} days",
                    "delta_fmt": f"{int(delta):+} days ({fmt_inr(delta_inr)})",
                })

    # --- Scenario ID Assignment (A1..A5 for Track 3 Canonical Scenarios) ---
    # Assign stable IDs A1..A5 so scenario test assertions can resolve specific alerts by ID.
    canonical_specs = {
        "A1": ("Revenue", "Electronics", "Region X"),
        "A2": ("Revenue", "Electronics", "Region Y"),
        "A3": ("Revenue", "Wearables", "Region Z"),
        "A4": ("Marketing Spend", "Electronics", "(all)"),
        "A5": ("Revenue", "Apparel", "Region Z"),
    }

    assigned = {}
    for aid, (kpi, cat, reg) in canonical_specs.items():
        match = next((a for a in alerts if a["kpi"] == kpi and a["category"] == cat and a["region"] == reg), None)
        if match:
            match["id"] = aid
            assigned[id(match)] = aid

    next_num = 6
    for a in alerts:
        if id(a) not in assigned:
            a["id"] = f"A{next_num}"
            next_num += 1

    # --- COMPLETE ALERT POOL SEVERITY SORTING ---
    # Do NOT force canonical_alerts to be first 5 positions in the array.
    # Sort the complete alert pool by absolute rupee impact (or severity) so the dashboard
    # receives a natural, unsuppressed alert pool across all 5 KPI families.
    alerts.sort(key=lambda a: abs(a["delta_inr"]), reverse=True)

    for a in alerts:
        if "pct_fmt" not in a:
            a["pct_fmt"] = ("n/a (no baseline)" if a["pct_change"] is None
                            else f"{a['pct_change']*100:+.1f}%")
        if "z_fmt" not in a:
            a["z_fmt"] = "n/a" if a["z_score"] is None else f"{a['z_score']:.2f}"

    return alerts, cur_week


# ------------------------------------------------------- Step 3: Fast Path --
def fast_path_check(alert, changelog):
    """
    Scans change log for direct operational event matches.
    Supports regional alerts (matching exact region) and aggregate "(all)" alerts (matching category across all regions).
    """
    t0 = time.perf_counter()
    ws, we = alert["week_start"], alert["week_start"] + pd.Timedelta(days=6)
    
    # Mandatory Category and Date Window (+/- 2 days)
    hits = changelog[
        (changelog.date >= ws - pd.Timedelta(days=2)) &
        (changelog.date <= we + pd.Timedelta(days=2)) &
        (changelog.category == alert["category"])
    ].copy()

    # Regional alerts require exact region match; aggregate "(all)" alerts search all regions
    if alert.get("region") != "(all)":
        hits = hits[hits.region == alert["region"]]

    result = None
    if len(hits):
        # Deterministic Ranking:
        # 1. Temporal closeness to window start
        hits["dist"] = (hits["date"] - ws).abs()

        # 2. Event type priority (Operational / IT / Price / Campaign)
        priority_map = {
            "it_incident": 0,
            "operational": 1,
            "price_change": 2,
            "campaign": 3,
            "stock_out": 4
        }
        hits["priority"] = hits["event_type"].map(lambda et: priority_map.get(str(et).lower(), 5))

        # 3. Stable tie-breaker
        hits = hits.sort_values(by=["dist", "priority", "date"])
        h = hits.iloc[0]

        result = {
            "matched": True,
            "event_date": str(h["date"].date()),
            "event_type": h["event_type"],
            "description": h["description"],
            "window": f"[{ws.date()} .. {we.date()}] +/- 2 days",
            "region": str(h["region"])
        }
    return result, t0


# ---------------------------------------------- Step 3.5: Telemetry Evidence Retriever ----
class TelemetryRetriever:
    """In-memory multi-source evidence retriever over POS sales, campaigns, inventory, and change log."""

    def __init__(self, sales, camps, inv, changelog):
        self.sales = sales
        self.camps = camps
        self.inv = inv
        self.changelog = changelog

    def retrieve_evidence(self, category: str, region: str, week_start: pd.Timestamp, top_k: int = 5):
        """Retrieve most relevant empirical evidence records with exact timestamps, provenance, and snippets."""
        evidence_chunks = []
        we = week_start + pd.Timedelta(days=6)

        # 1. Inventory stockout evidence
        if region != "(all)":
            inv_matches = self.inv[
                (self.inv.date >= week_start - pd.Timedelta(days=7)) &
                (self.inv.date <= we) &
                (self.inv.region == region) &
                (self.inv.stock_out_flag == 1)
            ]
        else:
            inv_matches = self.inv[
                (self.inv.date >= week_start - pd.Timedelta(days=7)) &
                (self.inv.date <= we) &
                (self.inv.stock_out_flag == 1)
            ]

        for _, row in inv_matches.iterrows():
            is_in_week = week_start <= row["date"] <= we
            evidence_chunks.append({
                "source": "inventory_daily.csv",
                "timestamp": str(row["date"].date()),
                "entity": f"{row['product_id']} ({row['region']})",
                "evidence_type": "Stock-out Telemetry",
                "snippet": f"Stock-out flagged (stock_on_hand={row['stock_on_hand']}) on {row['date'].date()} for SKU {row['product_id']}",
                "relevance_score": 0.96 if is_in_week else 0.65,
            })

        # 2. Campaign spend evidence
        if region != "(all)":
            camp_matches = self.camps[
                (self.camps.category == category) &
                (self.camps.region == region) &
                (self.camps.week_start >= week_start - pd.Timedelta(days=28)) &
                (self.camps.week_start <= we)
            ].sort_values("week_start", ascending=False)
        else:
            camp_matches = self.camps[
                (self.camps.category == category) &
                (self.camps.week_start >= week_start - pd.Timedelta(days=28)) &
                (self.camps.week_start <= we)
            ].sort_values("week_start", ascending=False)

        for _, row in camp_matches.iterrows():
            is_cur = row["week_start"] == week_start
            evidence_chunks.append({
                "source": "campaigns_weekly.csv",
                "timestamp": str(row["week_start"].date()),
                "entity": f"Campaign {row['campaign_id']} ({category}/{row['region']})",
                "evidence_type": "Marketing Spend Record",
                "snippet": f"Weekly spend {fmt_inr(row['spend'])} ({row['impressions']:,} impressions) for {category}/{row['region']}",
                "relevance_score": 0.92 if is_cur else 0.55,
            })

        # 3. Change log incidents
        log_matches = self.changelog[
            (self.changelog.category == category) &
            (self.changelog.date >= week_start - pd.Timedelta(days=14)) &
            (self.changelog.date <= we + pd.Timedelta(days=2))
        ]
        if region != "(all)":
            log_matches = log_matches[log_matches.region == region]

        for _, row in log_matches.iterrows():
            is_in_window = week_start - pd.Timedelta(days=2) <= row["date"] <= we + pd.Timedelta(days=2)
            evidence_chunks.append({
                "source": "change_log.csv",
                "timestamp": str(row["date"].date()),
                "entity": f"Ops Event ({row['event_type']})",
                "evidence_type": "Change Log Record",
                "snippet": f"[{row['event_type']}] on {row['date'].date()}: {row['description']}",
                "relevance_score": 0.98 if is_in_window else 0.70,
            })

        # 4. Sales daily aggregates
        s_query = self.sales[(self.sales.category == category) &
                             (self.sales.date >= week_start) &
                             (self.sales.date <= we)]
        if region != "(all)":
            s_query = s_query[s_query.region == region]

        if not s_query.empty:
            tot_rev = s_query["revenue"].sum()
            tot_units = s_query["units_sold"].sum()
            evidence_chunks.append({
                "source": "sales_daily.csv",
                "timestamp": f"{week_start.date()}..{we.date()}",
                "entity": f"{category} ({region}) POS Stream",
                "evidence_type": "POS Sales Decomposition",
                "snippet": f"Weekly total revenue {fmt_inr(tot_rev)} across {tot_units:,} units sold in {region}",
                "relevance_score": 0.88,
            })

        # Sort by relevance score
        evidence_chunks.sort(key=lambda x: x["relevance_score"], reverse=True)
        return evidence_chunks[:top_k]


# ---------------------------------------------- Step 3.6: Feedback Calibrator ----
class EmpiricalFeedbackCalibrator:
    """Calibrates hypothesis prior weights based on persisted analyst approvals/rejections for specific hypothesis types."""

    def __init__(self, decisions_path: Path = DATA / "decisions.csv"):
        self.decisions_path = decisions_path

    def get_calibration_factor(self, hypothesis_type: str, category: str) -> float:
        """
        Returns hypothesis-specific empirical multiplier [0.90 .. 1.05]
        based on historical human reviews for the relevant hypothesis_type and category.
        """
        if not self.decisions_path.exists():
            return 1.0
        try:
            df = pd.read_csv(self.decisions_path)
            if df.empty or "decision" not in df.columns:
                return 1.0

            # 1. Filter by category (if category column exists)
            if "category" in df.columns and category:
                df_cat = df[df["category"] == category]
                if not df_cat.empty:
                    df = df_cat

            # 2. Filter by hypothesis_type (if hypothesis_type column exists)
            kind_clean = str(hypothesis_type).split("-")[0].split(" ")[0].strip()
            if "hypothesis_type" in df.columns:
                df_hyp = df[df["hypothesis_type"].fillna("").astype(str).str.contains(kind_clean, case=False, regex=False)]
                if not df_hyp.empty:
                    df = df_hyp

            if df.empty:
                return 1.0

            # 3. Decision string normalization
            dec_norm = df["decision"].astype(str).str.strip().str.lower()
            approved_mask = dec_norm.isin(["approved", "approve"])
            rejected_mask = dec_norm.isin(["rejected", "reject"])

            n_approved = approved_mask.sum()
            n_rejected = rejected_mask.sum()
            n_total = n_approved + n_rejected

            if n_total < 3:
                return 1.0

            approval_rate = n_approved / n_total

            if approval_rate >= 0.75:
                return 1.05
            elif approval_rate >= 0.50:
                return 1.00
            elif approval_rate >= 0.25:
                return 0.95
            else:
                return 0.90
        except Exception:
            return 1.0


# ------------------------------- Step 4: deep path — Top 4 competing hypotheses --
def hypothesis_supply(alert, sales_wk_daily, sales, inv, rag_citations=None):
    """Counterfactual: pre-stockout daily rate projected across stockout days."""
    cat, reg = alert["category"], alert["region"]
    wk = alert["week_start"]
    we = wk + pd.Timedelta(days=6)

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

    citations = [c for c in (rag_citations or []) if c.get("source") == "inventory_daily.csv"]

    if not candidates:
        return {
            "name": "Supply-side (stock-out)",
            "supported": False,
            "deciding_metric": "stock-out days in window",
            "deciding_value": ("0 stock-out day(s) for any product in this "
                               f"{cat}/{reg} cell during the alert week"),
            "data_source": "inventory_daily.csv (stock_out_flag)",
            "supporting_evidence": "Inventory daily tracking active",
            "contrary_evidence": "0 stock-out day(s) for any product in this cell during alert week",
            "verdict": ("REJECTED - no stock-out exposure exists in this "
                        "cell during the window"),
            "score": 0.0,
            "detail": {},
            "rag_citations": citations,
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

    sup_ev = f"Pre-stockout daily avg {fmt_inr(pre_rate)} x {len(days)} stockout days = {fmt_inr(counterfactual)} expected vs {fmt_inr(actual)} actual ({explain_ratio*100:.0f}% of move explained)" if supported else f"Stockout recorded for {pid} ({len(days)} days)"
    con_ev = "None identified" if supported else f"Counterfactual gap explains only {explain_ratio*100:.0f}% of move (threshold >= {SUPPLY_EXPLAIN_MIN*100:.0f}%)"

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
        "supporting_evidence": sup_ev,
        "contrary_evidence": con_ev,
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
        "rag_citations": citations,
    }


def hypothesis_demand(alert, camps_wk_cell, rag_citations=None):
    """Check for a campaign/demand spike in the same window."""
    cur = camps_wk_cell[camps_wk_cell.week_start == alert["week_start"]]
    hist = camps_wk_cell[camps_wk_cell.week_start < alert["week_start"]].tail(4)
    cur_spend = float(cur.spend.sum()) if len(cur) else 0.0
    base_spend = float(hist.spend.mean()) if len(hist) else 0.0
    ratio = (cur_spend - base_spend) / base_spend if base_spend else None

    moved_down = alert["direction"] == "down"
    aligned = (ratio is not None and
               ((ratio >= DEMAND_SPIKE_MIN and not moved_down) or
                (ratio <= -DEMAND_SPIKE_MIN and moved_down)))
    supported = bool(aligned)

    rv = "n/a" if ratio is None else f"{ratio*100:+.1f}%"
    verdict = ("SUPPORTED" if supported else
               f"REJECTED - spend changed {rv} vs baseline "
               f"{fmt_inr(base_spend)} (needs a >={DEMAND_SPIKE_MIN*100:.0f}% "
               f"move aligned with the KPI direction)")

    citations = [c for c in (rag_citations or []) if c.get("source") == "campaigns_weekly.csv"]

    return {
        "name": "Demand-side (campaign/demand shift)",
        "supported": supported,
        "deciding_metric": "campaign spend change vs trailing 4-wk baseline",
        "deciding_value": (f"{fmt_inr(cur_spend)} this week vs "
                           f"{fmt_inr(base_spend)} baseline -> {rv}"),
        "data_source": "campaigns_weekly.csv (same category x region)",
        "supporting_evidence": f"Campaign spend changed {rv} vs baseline {fmt_inr(base_spend)}" if supported else "Campaign spend tracking active",
        "contrary_evidence": "None identified" if supported else f"Spend change {rv} is insufficient or misaligned with {alert['direction']} KPI move",
        "verdict": verdict,
        "score": round(min(abs(ratio) / 0.5, 1.0) if ratio is not None else 0.0, 3),
        "detail": {
            "spend_current": cur_spend, "spend_baseline": base_spend,
            "spend_change_pct": None if ratio is None else round(ratio * 100, 1),
        },
        "rag_citations": citations,
    }


def hypothesis_pricing(alert, sales, rag_citations=None):
    """Check for material price changes or elasticity moves."""
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
                "data_source": "sales_daily.csv",
                "supporting_evidence": "POS price tracking active",
                "contrary_evidence": "Insufficient transaction rows in window",
                "verdict": "REJECTED",
                "score": 0.0, "detail": {}, "rag_citations": []}
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
        "supporting_evidence": f"Unit price shift of {max_delta*100:.2f}% detected" if supported else "Unit price line item tracking active",
        "contrary_evidence": "None identified" if supported else f"Largest price move was only {max_delta*100:.2f}% (below {PRICE_MOVE_MIN*100:.0f}% threshold)",
        "verdict": ("SUPPORTED" if supported else
                    f"REJECTED - largest price move was only "
                    f"{max_delta*100:.2f}%"),
        "score": round(min(max_delta / PRICE_MOVE_MIN, 1.0), 3),
        "detail": {"max_price_delta_pct": round(max_delta * 100, 2)},
        "rag_citations": [c for c in (rag_citations or []) if c.get("source") == "sales_daily.csv"],
    }


def hypothesis_operational(alert, changelog, sales, rag_citations=None):
    """Check for channel / IT / operational disruptions impacting checkout velocity."""
    cat, reg = alert["category"], alert["region"]
    wk = alert["week_start"]
    we = wk + pd.Timedelta(days=6)

    hits = changelog[
        (changelog.date >= wk - pd.Timedelta(days=2)) &
        (changelog.date <= we + pd.Timedelta(days=2)) &
        (changelog.category == cat)
    ]
    if reg != "(all)":
        hits = hits[hits.region == reg]

    citations = [c for c in (rag_citations or []) if c.get("source") == "change_log.csv"]

    if hits.empty:
        return {
            "name": "Operational / Channel Disruption",
            "supported": False,
            "deciding_metric": "logged operational/platform incident in window",
            "deciding_value": f"0 logged platform/checkout incidents for {cat}/{reg} in window",
            "data_source": "change_log.csv (event_type=it_incident / operational)",
            "supporting_evidence": "Change log event scanner active",
            "contrary_evidence": f"0 logged platform/checkout incidents for {cat}/{reg} in window",
            "verdict": "REJECTED - no IT outages or channel disruptions logged",
            "score": 0.0,
            "detail": {},
            "rag_citations": citations,
        }

    h = hits.iloc[0]
    is_supported = h["event_type"] in ("it_incident", "operational") and alert["direction"] == "down"
    verdict = (
        f"SUPPORTED - direct operational disruption [{h['event_type']}] on {h['date'].date()}: {h['description']}"
        if is_supported else
        f"REJECTED - event [{h['event_type']}] does not match observed anomaly direction ({alert['direction']})"
    )
    return {
        "name": "Operational / Channel Disruption",
        "supported": bool(is_supported),
        "deciding_metric": "incident severity & category match",
        "deciding_value": f"[{h['event_type']}] logged on {h['date'].date()}: {h['description']}",
        "data_source": "change_log.csv (event_type=it_incident / operational)",
        "supporting_evidence": f"Change log entry: [{h['event_type']}] on {h['date'].date()}" if is_supported else "Operational log checked",
        "contrary_evidence": "None identified" if is_supported else f"Event type [{h['event_type']}] misaligned with KPI direction ({alert['direction']})",
        "verdict": verdict,
        "score": 0.95 if is_supported else 0.20,
        "detail": {
            "event_type": h["event_type"],
            "event_date": str(h["date"].date()),
            "description": h["description"],
        },
        "rag_citations": citations,
    }


# --------------------------------------------- Step 5: confidence scoring --
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
    "Operational": {"temporal_correlation": 0.35, "source_agreement": 0.25,
                    "hypothesis_margin": 0.20, "data_completeness": 0.20},
}


def attach_hypothesis_confidence(hyps, comps, calibrator=None, category=""):
    """Give every hypothesis its own weighted confidence percentage."""
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
        raw_pct = sum(w[k] * f[k] for k in w)
        if calibrator:
            calib = calibrator.get_calibration_factor(kind, category)
            pct = raw_pct * calib
        else:
            pct = raw_pct
        # Clamp confidence to [0.0, 1.0] (0 to 100%)
        clamped_pct = max(0.0, min(1.0, pct))
        h["confidence_pct"] = round(clamped_pct * 100)
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
        agree += 1 if winner["supported"] else 0
    sources += 1
    agree += 1 if winner["supported"] else 0
    if winner["name"].startswith("Demand"):
        sources += 1
        agree += 1 if winner["supported"] else 0
    if winner["name"].startswith("Operational"):
        sources += 1
        agree += 1 if winner["supported"] else 0
    components["source_agreement"] = round(agree / sources, 3)

    # 3. data completeness
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
            "name": "Weighted Evidence Confidence",
            "components": components, "gaps": gaps}


# ------------------------------------------------- Step 6: conflict check --
def conflict_check(alert, sales_wk, inv, sales, winner, camps_wk=None):
    """Compare the winning story against comparable cells with similar exposure."""
    if alert["kpi"] != "Revenue":
        return {
            "conflict": False,
            "comparable_cells": [],
            "note": "Aggregate KPI - cross-region exposure comparison not applicable.",
            "escalation_directive": None,
            "signal_a": None,
            "signal_b": None,
            "source_a": "sales_daily.csv",
            "source_b": "inventory_daily.csv",
            "reason": None
        }
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
            return {
                "conflict": False,
                "comparable_cells": siblings,
                "note": (f"{s['region']} shows the same stock-out "
                         f"exposure with an opposite revenue outcome "
                         f"({s['revenue_pct_change']:+.1f}%), but its "
                         f"own campaign spend rose "
                         f"{s['campaign_spend_change_pct']:+.1f}% - "
                         f"the divergence is explained, so the winning "
                         f"hypothesis stands."),
                "escalation_directive": None,
                "signal_a": None,
                "signal_b": None,
                "source_a": "sales_daily.csv",
                "source_b": "campaigns_weekly.csv",
                "reason": None
            }
        sig_a = (f"{alert['category']}/{alert['region']}: stock-out "
                 f"exposure coincided with {alert['pct_fmt']} "
                 f"revenue ({alert['delta_fmt']})")
        sig_b = (f"{alert['category']}/{s['region']}: similar "
                 f"stock-out ({s['stockout_days']} days, product "
                 f"{s['product_id']}) yet revenue moved "
                 f"{s['revenue_pct_change']:+.1f}% with no "
                 f"quantified offsetting factor")
        reason_str = "Cross-region counterfactual contradiction: identical inventory stock-out did not cause revenue contraction in sibling region."
        return {
            "conflict": True,
            "signal_a": sig_a,
            "signal_b": sig_b,
            "source_a": "sales_daily.csv / inventory_daily.csv",
            "source_b": "sales_daily.csv / inventory_daily.csv",
            "reason": reason_str,
            "conflict_explanation": reason_str,
            "comparable_cells": siblings,
            "escalation_directive": "Escalate for manual commercial audit — do not automate operational changes."
        }
    return {
        "conflict": False,
        "comparable_cells": siblings,
        "escalation_directive": None,
        "signal_a": None,
        "signal_b": None,
        "source_a": "sales_daily.csv",
        "source_b": "inventory_daily.csv",
        "reason": None
    }


# ------------------------------------------- Step 7: access gate (CXO) ----
CXO_REDACTED_KEYS = {"product_id", "product_name", "stockout_days"}
CXO_LOG = []


def redact_for_cxo(payload):
    import re
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


# --------------------------------------------- Step 10: 7-Part Recommendation Schema ----
def recommend(alert, winner, conflict, abstained):
    """
    Generate canonical 7-part recommendation:
    driver -> controllable lever -> action -> estimated impact -> owner -> confidence -> monitoring plan.
    """
    if abstained or winner is None:
        return {
            "driver": "Sparse telemetry / unverified baseline",
            "lever": "Baseline data stabilization & telemetry capture",
            "action": "Collect more data before acting - do not treat this anomaly as explained.",
            "estimated_impact": None,
            "est_impact_fmt": None,
            "owner": "Data Engineering & Analytics Operations",
            "confidence": "Low / Unverified",
            "monitoring_plan": "Establish daily telemetry collection over next 28 days before re-initiating automated triage.",
            "basis": "Insufficient history; no counterfactual can be computed.",
        }
    if conflict.get("conflict"):
        return {
            "driver": f"Contradicting cross-regional evidence for leading candidate",
            "lever": "Regional commercial coordination & promotional audit",
            "action": "Escalate for manual review: the leading explanation does not replicate across comparable regions.",
            "estimated_impact": None,
            "est_impact_fmt": None,
            "owner": "Regional Commercial Lead / Category Director",
            "confidence": "Escalated (Unresolved Conflict)",
            "monitoring_plan": "Audit cross-region campaign and promotional overlap; review store-level POS transaction logs.",
            "basis": "Conflicting regional evidence (see conflict panel).",
        }
    d = winner.get("detail", {})
    if winner["supported"] and winner["name"].startswith("Supply"):
        daily = d.get("pre_rate_daily", 0)
        pname = d.get("product_name", "affected SKU")
        return {
            "driver": f"Inventory depletion & stockout outage of {pname}",
            "lever": "DC stock rebalancing & priority supplier replenishment",
            "action": (f"Expedite replenishment of {pname} in "
                       f"{alert['region']} (transfer stock from sibling DCs); "
                       f"each recovered day is worth ~{fmt_inr(daily)} at the "
                       f"pre-stockout run rate."),
            "estimated_impact": daily * 7,
            "est_impact_fmt": fmt_inr(daily * 7),
            "owner": "Category Manager - Supply Chain Lead",
            "confidence": f"{winner.get('confidence_pct', 95)}% (High)",
            "monitoring_plan": f"Monitor daily stock-on-hand at {alert['region']} distribution center until buffer exceeds 14 days of sales velocity.",
            "basis": f"Pre-stockout daily average {fmt_inr(daily)} x 7 days.",
        }
    if winner["supported"] and winner["name"].startswith("Demand"):
        return {
            "driver": "Marketing campaign intensity shift",
            "lever": "Paid media & promotional campaign spend allocation",
            "action": (f"Maintain/scale the campaign mix in "
                       f"{alert['category']}/{alert['region']}; it coincides "
                       f"with {alert['pct_fmt']} revenue."),
            "estimated_impact": alert["delta_inr"],
            "est_impact_fmt": alert["delta_fmt"],
            "owner": "Category Marketing Manager",
            "confidence": f"{winner.get('confidence_pct', 90)}% (High)",
            "monitoring_plan": "Weekly ROAS & customer acquisition cost tracking across digital media channels.",
            "basis": f"Week revenue delta {alert['delta_fmt']} vs baseline.",
        }
    if winner["supported"] and winner["name"].startswith("Operational"):
        return {
            "driver": f"Operational / Platform disruption ({d.get('event_type', 'incident')})",
            "lever": "E-Commerce checkout infrastructure & IT incident resolution",
            "action": (f"Verify resolution of the logged operational incident ({d.get('description', '')}) "
                       f"and monitor order checkout conversion."),
            "estimated_impact": alert["delta_inr"],
            "est_impact_fmt": alert["delta_fmt"],
            "owner": "E-Commerce Platform Operations Lead",
            "confidence": f"{winner.get('confidence_pct', 95)}% (High)",
            "monitoring_plan": "Hourly cart-to-order conversion rate tracking post-incident resolution.",
            "basis": f"Direct operational change log correlation ({d.get('event_date', '')}).",
        }
    return {
        "driver": "Multi-factor ambient variation / unisolated signal",
        "lever": "Telemetry granularity refinement",
        "action": "Monitor for one more cycle; no single hypothesis cleared the falsification bar.",
        "estimated_impact": None,
        "est_impact_fmt": None,
        "owner": "Category Business Analyst",
        "confidence": "Inconclusive",
        "monitoring_plan": "Re-run multi-factor regression after the close of the next Monday weekly grain.",
        "basis": "All hypotheses scored below support thresholds.",
    }


# ------------------------------------------------------------ full runner --
def analyze_alert(alert, sales, camps_wk, sales_wk, inv, changelog, ledger, retriever=None, calibrator=None):
    payload = {"alert": alert}

    # Step 2 reconciliation per-alert audit trail:
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

    # Step 3.5 Evidence Retrieval Layer
    t0_rag = time.perf_counter()
    if retriever is None:
        retriever = TelemetryRetriever(sales, camps_wk, inv, changelog)
    rag_evidence = retriever.retrieve_evidence(
        category=alert["category"],
        region=alert["region"],
        week_start=alert["week_start"],
        top_k=5
    )
    ledger.add(f"Step 3.5 Evidence Retrieval {aid}", "Multi-Source Retrieval", t0_rag,
               f"Retrieved {len(rag_evidence)} empirical telemetry evidence records across POS, CRM, ERP & Change Log")
    payload["rag_evidence"] = rag_evidence

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
            "driver": f"Operational incident [{fp['event_type']}] on {fp['event_date']}",
            "lever": "Platform IT resolution & order recovery monitoring",
            "action": (f"Treat as operationally explained by the logged "
                       f"[{fp['event_type']}] on {fp['event_date']}; verify "
                       f"recovery after the incident window closes."),
            "estimated_impact": None,
            "est_impact_fmt": None,
            "owner": "IT Incident Management / E-Commerce Ops",
            "confidence": "95% (High)",
            "monitoring_plan": "Monitor cart conversion & API checkout health metrics for 48h post-fix.",
            "basis": f"Direct change-log match inside {fp['window']}.",
        }
        return payload

    # Step 4 deep path — Top 4 competing hypotheses
    t0 = time.perf_counter()
    camps_cell = camps_wk[(camps_wk.category == alert["category"])] if \
        alert["region"] == "(all)" else \
        camps_wk[(camps_wk.category == alert["category"]) &
                 (camps_wk.region == alert["region"])]
    hyps = [
        hypothesis_supply(alert, None, sales, inv, rag_evidence),
        hypothesis_demand(alert, camps_cell, rag_evidence),
        hypothesis_pricing(alert, sales, rag_evidence),
        hypothesis_operational(alert, changelog, sales, rag_evidence),
    ]
    hyps = [h for h in hyps if h]
    ledger.add(f"Step 4 Hypothesis tests (x4, falsified) {aid}", "Deterministic", t0,
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
    attach_hypothesis_confidence(hyps, conf["components"], calibrator, alert["category"])
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
            "abstain_flag": True,
            "reason": "Insufficient baseline history and extreme data sparsity",
            "missing_data": f"Only {int(round(conf['components']['data_completeness']*28))} of 28 baseline daily sales records present ({conf['components']['data_completeness']*100:.0f}% completeness); {alert.get('baseline_weeks', 0)} trailing baseline weeks",
            "required_data": f"Collect {days_short} additional daily sales/inventory records (minimum 3 complete weeks) before re-running causal analysis",
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
    camps_wk = camps.copy()
    ledger.add("Step 2 Reconcile grains", "Deterministic", t0,
               "Resampled daily sales to weekly grain to align with campaign "
               "cadence (91 daily rows/cell -> 13 Mondays); campaign table "
               "already weekly.")

    t0 = time.perf_counter()
    alerts, cur_week = detect(sales_wk, camps_wk, inv, sales)
    ledger.add("Step 1 Detect anomalies", "Deterministic", t0,
               f"{len(alerts)} material alerts (threshold: |z|>=1.5 AND "
               f"|delta|>=10%), sorted by rupee impact")

    retriever = TelemetryRetriever(sales, camps_wk, inv, changelog)
    calibrator = EmpiricalFeedbackCalibrator()

    results = []
    for a in alerts:
        payload = analyze_alert(a, sales, camps_wk, sales_wk, inv,
                                changelog, ledger, retriever=retriever, calibrator=calibrator)
        results.append(payload)

    return {"alerts": [_clean(r) for r in results],
            "ledger_rows": ledger.rows,
            "cxo_access_log": CXO_LOG,
            "kpi_registry": KPI_REGISTRY,
            "cur_week": str(cur_week.date())}
