import itertools
import random
from typing import Mapping, List

from pandas import DataFrame, Series

from BL.eval_result import EvalResult
from BL.indicators import Indicators
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.Tracer import Tracer
from datetime import datetime


class BasePredictor:
    """Klasse, die als Basis dient.

            Attributes:
                indicators (Indicators): Indikatoren
            """

    def __init__(self, symbol: str, indicators, config=None, tracer: Tracer = ConsoleTracer()):
        self._limit = 10
        self._stop = 20
        self._id = ""
        self._active = True
        self._use_isl = False
        self._isl_open_end = False
        self._isl_distance = 6.0
        self._isl_factor = 0.7
        self._isl_entry = self._stop * 0.7
        self._symbol = symbol
        self._result: EvalResult = EvalResult()
        self._indicator_names = [Indicators.RSI, Indicators.EMA]


        if config is None:
            config = {}
        self.setup(config)
        self._tracer = tracer
        self._indicators = indicators

    def __str__(self):
        return f"Indicatornames {self._indicator_names} Limit {self._limit} Stop {self._stop} ISL {self._use_isl} Open End {self._isl_open_end} Dist {self._isl_distance} Fact {self._isl_entry}"

    def get_indicator_names(self) ->list:
        return self._indicator_names

    def setup(self, config):

        self._set_att(config, "_id")
        self._set_att(config, "_limit")
        self._set_att(config, "_stop")
        self._set_att(config, "_active")
        self._set_att(config, "_symbol")
        self._set_att(config, "_use_isl")
        self._set_att(config, "_isl_distance")
        self._set_att(config, "_isl_factor")
        self._set_att(config, "_isl_entry")
        self._set_att(config, "_isl_open_end")
        self._limit = config.get("limit", self._limit)
        self._stop = config.get("stop", self._stop)
        self._result = EvalResult(symbol=config.get("_symbol", self._symbol),len_df=config.get("_len_df", 0),
                                  trade_minutes=config.get("_trade_minutes", 0),
                                  adapted_isl_distance=config.get("_adapted_isl_distance",False),
                                  median_profit=config.get("_median_profit",-10000),
                                  scan_time=config.get("_scan_time", datetime(1970, 1, 1)))
        self._result.set_result(config.get("_reward", 0), config.get("_trades", 0), config.get("_wins", 0))

    def get_id(self) -> str:
        return self._id

    def get_symbol(self) -> str:
        return self._symbol

    def get_stop(self) -> float:
        return self._stop

    def get_limit(self) -> float:
        return self._limit

    def get_open_limit_isl(self) -> bool:
        return self._isl_open_end

    def get_isl_factor(self) -> float:
        return self._isl_factor

    def get_isl_distance(self) -> float:
        return self._isl_distance

    def get_isl_entry(self) -> float:
        return self._isl_entry

    def use_isl(self) -> bool:
        return self._use_isl

    def activate(self):
        self._active = True

    def is_active(self) -> bool:
        return self._active

    def _set_att(self, config: dict, name: str):
        if name in config:
            self.__setattr__(name, config[name])
        else:
            if hasattr(self, name):
                self.__setattr__(name, self.__getattribute__(name))
            else:
                self.__setattr__(name, None)  # or any default value you'd prefer

    def predict(self, df: DataFrame) -> str:
        raise NotImplementedError

    def get_last_scan_time(self):
        return self._result.get_scan_time()

    def train(self, df_train: DataFrame, df_eval: DataFrame, analytics, symbol: str, epic: str,  scaling: int) -> EvalResult:
        ev_result: EvalResult = analytics.evaluate(self, df=df_train, df_eval=df_eval, only_one_position=False,
                                                   symbol=symbol, scaling=scaling, epic=epic)
        self._result = ev_result
        return ev_result

    def get_signals(self, df_train: DataFrame, analytics) -> DataFrame:
        return analytics.get_signals(self, df=df_train)


    def eval(self, df_train: DataFrame,
             df_eval: DataFrame,
             analytics,
             symbol: str,
             epic: str,
             scaling: int,
             only_one_position=False) -> EvalResult:
        ev_result: EvalResult = analytics.evaluate(self, df=df_train, df_eval=df_eval, only_one_position=only_one_position,
                                                   symbol=symbol, scaling=scaling,epic=epic)
        self._result = ev_result
        return ev_result

    def get_config(self):
        return Series([self.__class__.__name__,
                       self._stop,
                       self._limit,
                       self._active,
                       self._symbol,
                       self._use_isl,
                       self._isl_open_end,
                       self._isl_factor,
                       self._isl_distance,
                       self._isl_entry,
                       ],
                      index=["_type",
                             "_stop",
                             "_limit",
                             "_active",
                             "_symbol",
                             "_use_isl",
                             "_isl_open_end",
                             "_isl_factor",
                             "_isl_distance",
                             "_isl_entry"
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
    def _isl_trainer():

        json_objs = []
        json_objs.append({
            "_use_isl": False,
        })
        json_objs.append({
            "_use_isl": True,
            "_isl_open_end": False
        })
        json_objs.append({
            "_use_isl": True,
            "_isl_open_end": True
        })

        for entry, distance in itertools.product(random.choices(range(5,50), k=2), random.choices(range(6,30), k=2)):
            json_objs.append({
                "_use_isl": True,
                "_isl_open_end": True,
                "_isl_entry": entry,
                "_isl_distance": distance
            })
        for entry, distance in itertools.product(random.choices(range(5,50), k=2), random.choices(range(6,30), k=2)):
            json_objs.append({
                "_use_isl": True,
                "_isl_open_end": False,
                "_isl_entry": entry,
                "_isl_distance": distance
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
