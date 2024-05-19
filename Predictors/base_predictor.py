import itertools
import random

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

    version = "V2.0"
    fallback_model_version = ""


    def __init__(self, indicators, config=None , cache: BaseCache = BaseCache(), tracer: Tracer = ConsoleTracer()):
        self.limit = 10
        self.stop = 20
        self.last_scan = datetime(1970, 1, 1).isoformat()
        self._last_scan: EvalResult = EvalResult()

        if config is None:
            config = {}
        self.setup(config)
        self._tracer = tracer
        self.lastState = ""
        self._cache = cache
        self._indicators = indicators
        self.model_version = ""

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

    def predict(self, df: DataFrame) -> str:
        raise NotImplementedError

    def get_last_scan_time(self):
        return datetime.fromisoformat(self.last_scan)

    def train(self, df_train: DataFrame, df_eval: DataFrame, analytics, symbol:str, scaling:int) -> EvalResult:
        ev_result: EvalResult = analytics.evaluate(self, df=df_train, df_eval=df_eval, only_one_position=True, symbol=symbol, scaling=scaling)
        return ev_result

    def eval(self, df_train: DataFrame, df_eval: DataFrame, analytics, symbol: str, scaling:int) -> EvalResult:
        ev_result: EvalResult = analytics.evaluate(self, df=df_train, df_eval=df_eval, only_one_position=True,
                                                   symbol=symbol, scaling=scaling)
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
                random.choices(range(20,65), k=3),
                random.choices(range(6,25), k=3)):
            json_objs.append({
                "stop": stop,
                "limit": limit,
                "version": version
            })
        return json_objs

    @staticmethod
    def get_training_sets(version: str):
        return []

    def _get_filename(self, symbol, model_version: str):
        return f"{self.__class__.__name__}_{symbol}{model_version}.json"

    def set_result(self, result: EvalResult):
        self._last_scan = result

    def get_last_result(self) -> EvalResult:
        return self._last_scan

    def get_save_data(self) -> Series:
        self.last_scan = datetime.utcnow().isoformat()
        return self.get_config().append(self._last_scan.get_data())

    def save(self, symbol: str):

        self._cache.save_settings(self.get_save_data().to_json(), self._get_filename(symbol, self.model_version))

    def load(self, symbol: str):
        json = self._cache.load_settings(self._get_filename(symbol,self.model_version))
        if json is None:
            json = self._cache.load_settings(self._get_filename(symbol,self.fallback_model_version))

        if json is not None:
            self.setup(json)

        return self
