import itertools
import random
from typing import Mapping
from pandas import DataFrame, Series
from BL.indicators import Indicators
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.Tracer import Tracer


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

    def get_signals(self, df_train: DataFrame, analytics) -> DataFrame:
        return analytics.get_signals(self, df=df_train)


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

    def get_save_data(self) -> Mapping:
        return self.get_config().to_dict()

    def set_tracer(self, tracer):
        self._tracer = tracer
