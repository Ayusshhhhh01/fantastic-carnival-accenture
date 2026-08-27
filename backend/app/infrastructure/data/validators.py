from collections.abc import Mapping

import pandas as pd


REQUIRED_COLUMNS: Mapping[str, set[str]] = {
    "sales": {"date", "product_id", "category", "region", "units_sold", "unit_price", "revenue"},
    "campaigns": {"week_start", "category", "region", "spend"},
    "inventory": {"date", "product_id", "region", "stock_out_flag"},
    "change_log": {"date", "category", "region", "event_type"},
}


def validate_frames(frames: tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]) -> None:
    for (name, required), frame in zip(REQUIRED_COLUMNS.items(), frames):
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"{name} is missing required columns: {sorted(missing)}")
        if frame.empty:
            raise ValueError(f"{name} contains no rows")
