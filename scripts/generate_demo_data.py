import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cause.data_gen import build_campaigns, build_change_log, build_inventory, build_sales


def main() -> None:
    sales = build_sales()
    build_campaigns(sales).to_csv("cause/data/campaigns_weekly.csv", index=False)
    sales.to_csv("cause/data/sales_daily.csv", index=False)
    build_inventory(sales).to_csv("cause/data/inventory_daily.csv", index=False)
    build_change_log().to_csv("cause/data/change_log.csv", index=False)


if __name__ == "__main__":
    main()
