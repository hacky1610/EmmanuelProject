from pathlib import Path
import os
import json
from datetime import timedelta, date, datetime


def get_project_dir():
    return Path(__file__).parent.parent


class BaseReader:

    def get(self, key: str):
        raise NotImplementedError


class ConfigReader(BaseReader):
    _config = {}

    def __init__(self, account_type: str = "DEMO"):
        if account_type == "DEMO":
            path = "Config/demo.json"
        else:
            path = "Config/live.json"

        with open(os.path.join(get_project_dir(), path)) as f:
            self._config = json.load(f)

    def get(self, key: str):
        return self._config[key]


class EnvReader(BaseReader):

    def get(self, key: str):
        return os.getenv(key)


def load_train_data(symbol: str, ti, dp, trade_type):
    df = ti.load_data_by_date(symbol, "2023-02-20", "2023-04-13", dp, "1hour", trade_type=trade_type)
    df_eval_1 = ti.load_data_by_date(symbol, "2023-02-20", "2023-03-18", dp, "5min", trade_type=trade_type)
    df_eval_2 = ti.load_data_by_date(symbol, "2023-03-17", "2023-04-13", dp, "5min", trade_type=trade_type)

    df_complete = df_eval_1.append(df_eval_2[df_eval_2.date > df_eval_1.tail(1).date.values[0]])
    df_complete.reset_index(inplace=True)

    df.to_csv(f"Data/{symbol}_1hour.csv")
    df_complete.to_csv(f"Data/{symbol}_5min.csv")


class TimeUtils:

    @staticmethod
    def get_time_string(da: datetime):
        return da.strftime("%Y-%m-%dT%H:00:00.000Z")

    @staticmethod
    def get_date_string(da: date):
        return da.strftime("%Y-%m-%d")
