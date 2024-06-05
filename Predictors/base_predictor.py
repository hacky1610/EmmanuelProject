import itertools
import random
from typing import Mapping

from pandas import DataFrame, Series
from BL.eval_result import EvalResult
from Connectors.dropbox_cache import BaseCache
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.Tracer import Tracer
from datetime import datetime


class BasePredictor:
    """Klasse, die als Basis dient.

            Attributes:
                indicators (Indicators): Indikatoren
            """

    def __init__(self,symbol:str, indicators, config=None , tracer: Tracer = ConsoleTracer()):
        self._limit = 10
        self._stop = 20
        self._id = ""
        self._active = True
        self._symbol = symbol
        self._result: EvalResult = EvalResult()

        if config is None:
            config = {}
        self.setup(config)
        self._tracer = tracer
        self._indicators = indicators

    def setup(self, config):

        self._set_att(config, "_id")
        self._set_att(config, "_limit")
        self._set_att(config, "_stop")
        self._set_att(config, "_active")
        self._set_att(config, "_symbol")
        self._limit = config.get("limit", self._limit)
        self._stop = config.get("stop", self._stop)
        self._result = EvalResult(reward=config.get("_reward", 0.0),
                                  trades=config.get("_trades", 0),
                                  wins=config.get("_wins", 0),
                                  len_df=config.get("_len_df", 0),
                                  trade_minutes=config.get("_trade_minutes", 0),
                                  scan_time=config.get("_scan_time", datetime(1970, 1, 1)))

    def get_id(self) -> str:
        return self._id

    def get_symbol(self) -> str:
        return self._symbol

    def activate(self):
        self._active = True

    def is_active(self) -> bool:
        return self._active


    def _set_att(self, config: dict, name: str):
        self.__setattr__(name, config.get(name, self.__getattribute__(name)))

    def predict(self, df: DataFrame) -> str:
        raise NotImplementedError

    def get_last_scan_time(self):
        return self._result.get_scan_time()

    def train(self, df_train: DataFrame, df_eval: DataFrame, analytics, symbol:str, scaling:int, only_one_position = True) -> EvalResult:
        ev_result: EvalResult = analytics.evaluate(self, df=df_train, df_eval=df_eval, only_one_position=only_one_position, symbol=symbol, scaling=scaling)
        self._result = ev_result
        return ev_result

    def eval(self, df_train: DataFrame, df_eval: DataFrame, analytics, symbol: str, scaling:int) -> EvalResult:
        ev_result: EvalResult = analytics.evaluate(self, df=df_train, df_eval=df_eval, only_one_position=True,
                                                   symbol=symbol, scaling=scaling)
        self._result = ev_result
        return ev_result

    def get_config(self):
        return Series([self.__class__.__name__,
                       self._stop,
                       self._limit,
                       self._active,
                       self._symbol
                       ],
                      index=["_type",
                             "_stop",
                             "_limit",
                             "_active",
                             "_symbol"
                             ])

    @staticmethod
    def _stop_limit_trainer():

        json_objs = []
        for stop_limit in random.choices(range(15, 65), k=3):
            json_objs.append({
                "stop": stop_limit,
                "limit": stop_limit * random.choice([0.8, 1.0, 1.2])
            })
        return json_objs

    @staticmethod
    def get_training_sets():
        return []

    def set_result(self, result: EvalResult):
        self._result = result

    def get_result(self) -> EvalResult:
        return self._result

    def get_save_data(self) -> Mapping:
        return self.get_config().append(self._result.get_data()).to_dict()


