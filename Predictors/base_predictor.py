import itertools
import os
from pandas import DataFrame, Series
from BL.eval_result import EvalResult
from BL.utils import get_project_dir
from Connectors.dropbox_cache import BaseCache
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.Tracer import Tracer
import numpy as np
from datetime import datetime


class BasePredictor:
    SELL = "sell"
    BUY = "buy"
    NONE = "none"
    limit = 2.0
    stop = 2.0
    METRIC = "reward"
    version = "V1.0"
    model_version = ""
    last_scan = datetime(1970, 1, 1).isoformat()
    _tracer = ConsoleTracer()
    _last_scan: EvalResult = EvalResult()

    def __init__(self, config=None, cache: BaseCache = BaseCache(), tracer: Tracer = ConsoleTracer()):
        if config is None:
            config = {}
        self.setup(config)
        self._tracer = tracer
        self.lastState = ""
        self._cache = cache

    def setup(self, config):
        self._set_att(config, "limit")
        self._set_att(config, "stop")
        self._set_att(config, "version")
        self._set_att(config, "last_scan")
        self._last_scan = EvalResult(reward=config.get("_reward", 0.0),
                                     trades=config.get("_trades", 0),
                                     wins=config.get("_wins", 0),
                                     len_df=config.get("_len_df", 0),
                                     trade_minutes=config.get("_trade_minutes", 0))

    def _set_att(self, config: dict, name: str):
        self.__setattr__(name, config.get(name, self.__getattribute__(name)))

    def predict(self, df: DataFrame) -> (str, float, float):
        raise NotImplementedError

    def get_last_scan_time(self):
        return datetime.fromisoformat(self.last_scan)

    def step(self, df_train: DataFrame, df_eval: DataFrame, analytics) -> EvalResult:
        ev_result: EvalResult = analytics.evaluate(self, df_train, df_eval)
        self._last_scan = ev_result
        return ev_result

    def get_config(self):
        return Series([self.__class__.__name__,
                       self.stop,
                       self.limit,
                       self.version,
                       self.last_scan,
                       ],
                      index=["Type",
                             "stop",
                             "limit",
                             "version",
                             "last_scan",
                             ])

    @staticmethod
    def _stop_limit_trainer(version: str):

        json_objs = []
        for stop, limit in itertools.product(
                [1.8, 2.0, 2.3, 2.7, 3.],
                [1.8, 2.0, 2.3, 2.7, 3.]):
            json_objs.append({
                "stop": stop,
                "limit": limit,
                "version": version
            })
        return json_objs

    @staticmethod
    def get_training_sets(version: str):
        return []

    def _get_filename(self, symbol):
        return f"{self.__class__.__name__}_{symbol}{self.model_version}.json"

    def set_result(self, result: EvalResult):
        self._last_scan = result

    def get_last_result(self) -> EvalResult:
        return self._last_scan

    def save(self, symbol: str):
        self.last_scan = datetime.utcnow().isoformat()
        data = self.get_config().append(self._last_scan.get_data())
        self._cache.save_settings(data.to_json(), self._get_filename(symbol))

    def load(self, symbol: str):
        json = self._cache.load_settings(self._get_filename(symbol))
        if json is not None:
            self.setup(json)

        return self
