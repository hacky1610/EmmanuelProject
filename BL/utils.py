from pathlib import Path
import os
import json
from datetime import timedelta,date

def get_project_dir():
    return Path(__file__).parent.parent

class BaseReader:

    def get(self, key: str):
        raise NotImplementedError

    def get_float(self, key: str, default:float):
        raise NotImplementedError

class ConfigReader(BaseReader):
    _config = {}

    def __init__(self,live_config:bool=False):
        if live_config:
            path = "Config/live.json"
        else:
            path = "Config/demo.json"

        with open(os.path.join(get_project_dir(), path)) as f:
            self._config =  json.load(f)

    def get(self,key:str):
        return self._config[key]

    def get_float(self, key:str, default:float):
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






