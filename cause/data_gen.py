"""
CAUSE - Step 0: Synthetic data generator.

Bakes in exactly four scenarios:
  1. PRIMARY   : Electronics / Region X revenue drops ~18% in the final week.
                 Cause: top seller VoltX Pro 5G Phone stocked out 3 consecutive
                 days inside that week. Electronics campaign spend stays FLAT
                 (a real, checkable non-cause).
  2. CONFLICT  : Electronics / Region Y has a similar stock-out in the same
                 window but revenue does NOT drop (an offsetting promo spike).
                 A genuine contradiction for Step 6 to catch.
  3. SPARSE    : Wearables / Region Z product "PulseFit Band" has only 5 days
                 of history -> low completeness -> earned abstention.
  4. RED HERRING: no competitor/demand signal anywhere; demand-side hypothesis
                 honestly fails on the primary case.

Also emits change_log.csv containing a portal-outage event (fast-path case)
and deliberately NO entry for the electronics stock-outs (so the deep path
must run on the primary alert).
"""
import numpy as np
import pandas as pd
from pathlib import Path

np.random.seed(42)

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
DATA.mkdir(exist_ok=True)

START = pd.Timestamp("2026-05-25")
END = pd.Timestamp("2026-08-23")          # Sunday; final week = Aug 17–23
DATES = pd.date_range(START, END, freq="D")
STOCKOUT_DAYS = [pd.Timestamp("2026-08-19"), pd.Timestamp("2026-08-20"),
                 pd.Timestamp("2026-08-21")]   # Wed–Fri inside final week
ALERT_WEEK_START = pd.Timestamp("2026-08-17")

REGIONS = ["Region X", "Region Y", "Region Z"]
REGION_MULT = {"Region X": 1.00, "Region Y": 0.55, "Region Z": 0.35}

# product_id, name, category, unit_price, base units/day at Region X scale
CATALOG = [
    ("P101", "VoltX Pro 5G Phone",   "Electronics",     24999, 60),
    ("P102", "VoltX Lite 5G Phone",  "Electronics",     14999, 45),
    ("P103", "SoundCore Buds",       "Electronics",      2999, 90),
    ("P104", "NovaTab 11",           "Electronics",     18999, 22),
    ("P201", "UrbanDen Jacket",      "Apparel",          3499, 40),
    ("P202", "FlexiKnit Tee",        "Apparel",           999, 120),
    ("P203", "TrailBlaze Sneakers",  "Apparel",          4599, 30),
    ("P204", "CloudWeave Hoodie",    "Apparel",          2199, 35),
    ("P301", "ChefPro Blender",      "Home & Kitchen",   5499, 18),
    ("P302", "AeroFry Air Cooker",   "Home & Kitchen",   8999, 12),
    ("P303", "PureSip Bottle",       "Home & Kitchen",    899, 140),
    ("P304", "LoomNest Bedsheet",    "Home & Kitchen",   1799, 26),
    ("P401", "GlowLab Serum",        "Beauty",           1299, 70),
    ("P402", "SilkTouch Shampoo",    "Beauty",            449, 160),
    ("P403", "DewDrop Moisturizer",  "Beauty",            799, 95),
]
SPARSE_PRODUCT = ("P501", "PulseFit Band", "Wearables", 3999, None)


def weekday_factor(dow: int) -> float:
    # weekend lift for consumer goods
    return {5: 1.25, 6: 1.15}.get(dow, 1.0)


def build_sales() -> pd.DataFrame:
    rows = []
    for pid, name, cat, price, base in CATALOG:
        for region in REGIONS:
            mult = REGION_MULT[region]
            lam = base * mult
            for d in DATES:
                units = np.random.poisson(lam * weekday_factor(d.dayofweek) *
                                          np.random.uniform(0.85, 1.15))
                rows.append((d.date(), pid, name, cat, region, int(units),
                             float(price), float(units * price)))

    # ---- Scenario 3: sparse product, Region Z only, last 5 days only ----
    pid, name, cat, price, _ = SPARSE_PRODUCT
    sparse_units = [220, 35, 140, 15, 95]        # volatile launch-week sales
    for d, u in zip(pd.date_range("2026-08-19", "2026-08-23"), sparse_units):
        rows.append((d.date(), pid, name, cat, "Region Z", u,
                     float(price), float(u * price)))

    df = pd.DataFrame(rows, columns=["date", "product_id", "product_name",
                                     "category", "region", "units_sold",
                                     "unit_price", "revenue"])
    df["date"] = pd.to_datetime(df["date"])

    # ---- Scenario 1: stockout kills P101 sales in Region X (3 days) ----
    m = (df.product_id == "P101") & (df.region == "Region X") & \
        df.date.isin(STOCKOUT_DAYS)
    df.loc[m, ["units_sold", "revenue"]] = 0

    # ---- Scenario 2: same stockout hits P102 in Region Y ... ----
    m = (df.product_id == "P102") & (df.region == "Region Y") & \
        df.date.isin(STOCKOUT_DAYS)
    df.loc[m, ["units_sold", "revenue"]] = 0

    # ---- ... but an offsetting promo lifts other Electronics SKUs in Y ----
    promo = (df.category == "Electronics") & (df.region == "Region Y") & \
            (df.date >= ALERT_WEEK_START) & (~df.product_id.eq("P102"))
    df.loc[promo, "units_sold"] = (df.loc[promo, "units_sold"] * 1.40).astype(int)
    df.loc[promo, "revenue"] = df.loc[promo, "units_sold"] * df.loc[promo, "unit_price"]

    # ---- Fast-path case: Apparel/Z dip caused by logged portal outage ----
    outage = (df.category == "Apparel") & (df.region == "Region Z") & \
             (df.date >= pd.Timestamp("2026-08-18")) & \
             (df.date <= pd.Timestamp("2026-08-21"))
    df.loc[outage, "units_sold"] = (df.loc[outage, "units_sold"] * 0.35).astype(int)
    df.loc[outage, "revenue"] = df.loc[outage, "units_sold"] * df.loc[outage, "unit_price"]

    return df.sort_values(["date", "product_id", "region"]).reset_index(drop=True)


def build_campaigns(sales: pd.DataFrame) -> pd.DataFrame:
    weeks = pd.date_range(START, END - pd.Timedelta(days=6), freq="7D")
    cats = sorted(sales.category.unique())
    weekly_spend_base = {"Electronics": 800000, "Apparel": 450000,
                         "Home & Kitchen": 300000, "Beauty": 250000,
                         "Wearables": 120000}
    rows = []
    cid = 1000
    for w in weeks:
        for cat in cats:
            for region in REGIONS:
                spend = weekly_spend_base.get(cat, 200000) * \
                    REGION_MULT[region] * np.random.uniform(0.92, 1.08)
                rows.append((w.date(), f"C-{cid}", cat, region,
                             round(float(spend), 2), int(spend / 0.02)))
                cid += 1

    df = pd.DataFrame(rows, columns=["week_start", "campaign_id", "category",
                                     "region", "spend", "impressions"])
    df["week_start"] = pd.to_datetime(df["week_start"])

    # ---- Conflict-case fuel: Electronics/Region Y promo spend spike ----
    m = (df.week_start == ALERT_WEEK_START) & \
        (df.category == "Electronics") & (df.region == "Region Y")
    df.loc[m, "spend"] = df.loc[m, "spend"] * 3.2
    df.loc[m, "impressions"] = (df.loc[m, "impressions"] * 3.2).astype(int)

    # NOTE: Electronics/Region X spend intentionally untouched -> flat.
    return df


def build_inventory(sales: pd.DataFrame) -> pd.DataFrame:
    rows = []
    pairs = sales[["product_id", "region"]].drop_duplicates()
    rng = np.random.default_rng(7)
    for _, r in pairs.iterrows():
        series = sales[(sales.product_id == r.product_id) &
                       (sales.region == r.region)].set_index("date").index
        for d in series:
            rows.append((d, r.product_id, r.region,
                         int(rng.integers(40, 500)), 0))
    df = pd.DataFrame(rows, columns=["date", "product_id", "region",
                                     "stock_on_hand", "stock_out_flag"])
    df["date"] = pd.to_datetime(df["date"])

    def force_stockout(pid, region):
        m = (df.product_id == pid) & (df.region == region) & \
            df.date.isin(STOCKOUT_DAYS)
        df.loc[m, ["stock_on_hand", "stock_out_flag"]] = [0, 1]

    force_stockout("P101", "Region X")     # primary case
    force_stockout("P102", "Region Y")     # conflict case

    # one old harmless flag far from the window (realistic noise)
    old = (df.product_id == "P402") & (df.region == "Region Z") & \
          (df.date == pd.Timestamp("2026-06-10"))
    df.loc[old, ["stock_on_hand", "stock_out_flag"]] = [0, 1]
    return df.sort_values(["date", "product_id", "region"]).reset_index(drop=True)


def build_change_log() -> pd.DataFrame:
    return pd.DataFrame([
        ("2026-06-16", "Beauty", "Region Y", "marketing",
         "Teaser campaign for GlowLab serum launched"),
        ("2026-07-04", "Home & Kitchen", "Region X", "pricing",
         "Weekend coupon experiment on blenders"),
        ("2026-08-18", "Apparel", "Region Z", "it_incident",
         "E-commerce checkout portal outage - orders failing, cart abandonment"),
    ], columns=["date", "category", "region", "event_type", "description"])


if __name__ == "__main__":
    sales = build_sales()
    campaigns = build_campaigns(sales)
    inventory = build_inventory(sales)
    changelog = build_change_log()

    sales.to_csv(DATA / "sales_daily.csv", index=False)
    campaigns.to_csv(DATA / "campaigns_weekly.csv", index=False)
    inventory.to_csv(DATA / "inventory_daily.csv", index=False)
    changelog.to_csv(DATA / "change_log.csv", index=False)

    # sanity print of the four baked scenarios
    wk = sales.groupby(["category", "region",
                        pd.Grouper(key="date", freq="W-SUN")])["revenue"].sum()
    ex = wk.loc[("Electronics", "Region X")].sort_index()
    ey = wk.loc[("Electronics", "Region Y")].sort_index()
    print("Electronics/X last 2 weeks:",
          f"{ex.iloc[-2]:,.0f} -> {ex.iloc[-1]:,.0f} "
          f"({(ex.iloc[-1]/ex.iloc[-2]-1)*100:+.1f}%)")
    print("Electronics/Y last 2 weeks:",
          f"{ey.iloc[-2]:,.0f} -> {ey.iloc[-1]:,.0f} "
          f"({(ey.iloc[-1]/ey.iloc[-2]-1)*100:+.1f}%)")
    az = wk.loc[("Apparel", "Region Z")].sort_index()
    print("Apparel/Z last 2 weeks:",
          f"{az.iloc[-2]:,.0f} -> {az.iloc[-1]:,.0f} "
          f"({(az.iloc[-1]/az.iloc[-2]-1)*100:+.1f}%)")
    wz = wk.loc[("Wearables", "Region Z")].sort_index()
    print("Wearables/Z weeks:", len(wz), "| history days:",
          (sales.category == "Wearables").sum())
