from pathlib import Path
import os
import json
import time
from functools import wraps

def measure_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time

        hours, rem = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(rem, 60)
        print(
            f"Die Laufzeit von {func.__name__} betrug {int(hours):02}:{int(minutes):02}:{seconds:.2f} (Stunden:Minuten:Sekunden).")

        return result
    return wrapper

def get_project_dir():
    return Path(__file__).parent.parent

class BaseReader:

    def get(self, key: str):
        raise NotImplementedError

    def get_bool(self, key: str) -> bool:
        raise NotImplementedError

    def get_float(self, key:str, default:float):
        raise NotImplementedError

class ConfigReader(BaseReader):
    _config = {}


    def __init__(self, account_type: str = "DEMO"):
        if account_type == "DEMO":
            path = "demo.json"
        else:
            path = "live.json"

        with open(os.path.join(get_project_dir(), "Config", path)) as f:
            self._config = json.load(f)

    def get(self, key: str):
        return self._config[key]

    def get_bool(self, key: str) -> bool:
        return self.get(key)

    def get_float(self, key: str, default: float) -> float:
        return self._config.get(key, default)

class EnvReader(BaseReader):

    def get(self,key:str):
        return os.getenv(key)

    def get_float(self, key:str, default:float) -> float:
        return float(os.getenv(key,default))


def load_train_data(symbol:str,ti,dp,trade_type):
    df = ti.load_data_by_date(symbol, "2023-02-20", "2023-04-13", dp,"1hour",trade_type=trade_type)
    df_eval_1 = ti.load_data_by_date(symbol, "2023-02-20", "2023-03-18", dp,"5min",trade_type=trade_type)
    df_eval_2 = ti.load_data_by_date(symbol, "2023-03-17", "2023-04-13", dp, "5min",trade_type=trade_type)

    df_complete = df_eval_1.append(df_eval_2[df_eval_2.date > df_eval_1.tail(1).date.values[0]])
    df_complete.reset_index(inplace=True)

    df.to_csv(f"Data/{symbol}_1hour.csv")
    df_complete.to_csv(f"Data/{symbol}_5min.csv")






