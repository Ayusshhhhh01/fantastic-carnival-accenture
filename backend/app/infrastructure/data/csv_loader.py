from pathlib import Path

import pandas as pd


class CsvDataLoader:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def load(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        return (
            pd.read_csv(self.data_dir / "sales_daily.csv", parse_dates=["date"]),
            pd.read_csv(self.data_dir / "campaigns_weekly.csv", parse_dates=["week_start"]),
            pd.read_csv(self.data_dir / "inventory_daily.csv", parse_dates=["date"]),
            pd.read_csv(self.data_dir / "change_log.csv", parse_dates=["date"]),
        )
