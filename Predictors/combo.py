import itertools
import os.path
import json

from Connectors import BaseCache
from Predictors.base_predictor import BasePredictor
from pandas import DataFrame, Series
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer


class Combo(BasePredictor):

    # https://www.youtube.com/watch?v=6c5exPYoz3U
    rsi_upper_limit = 80
    rsi_lower_limit = 23
    period_1 = 2
    period_2 = 3
    peak_count = 0
    rsi_trend = 0.05
    bb_change = None

    def __init__(self, config=None, tracer: Tracer = ConsoleTracer(),cache: BaseCache = BaseCache()):
        super().__init__(config, tracer=tracer,cache=cache)
        if config is None:
            config = {}
        self.setup(config)

    def setup(self, config: dict):
        self.rsi_upper_limit = config.get("rsi_upper_limit", self.rsi_upper_limit)
        self.rsi_lower_limit = config.get("rsi_lower_limit", self.rsi_lower_limit)
        self.period_1 = config.get("period_1", self.period_1)
        self.period_2 = config.get("period_2", self.period_2)
        self.peak_count = config.get("peak_count", self.peak_count)
        self.rsi_trend = config.get("rsi_trend", self.rsi_trend)
        self.bb_change = config.get("bb_change", self.bb_change)
        super().setup(config)
        self.stop = 5
        self.limit = 5

    def get_config(self) -> Series:
        return Series(["RSI_BB",
                       self.stop,
                       self.limit,
                       self.rsi_upper_limit,
                       self.rsi_lower_limit,
                       self.period_1,
                       self.period_2,
                       self.peak_count,
                       self.rsi_trend,
                       self.bb_change,
                       self.version,
                       self.best_result,
                       self.best_reward,
                       self.frequence
                       ],
                      index=["Type", "stop", "limit", "rsi_upper_limit",
                             "rsi_lower_limit", "period_1", "period_2", "peak_count", "rsi_trend","bb_change", "version","best_result","best_reward","frequence"])


    def predict(self, df: DataFrame) -> str:
        if len(df) < 10:
            return BasePredictor.NONE

        current_macd = df[-1:].MACD.item()
        current_signal = df[-1:].SIGNAL.item()
        current_psar = df[-1:].PSAR.item()
        current_ema50 = df[-1:].EMA_50.item()
        current_ema20 = df[-1:].EMA_20.item()
        current_close = df[-1:].close.item()
        current_adx = df[-1:].ADX.item()
        current_rsi = df[-1:].RSI.item()

        period = df[-3:]


        if current_psar < current_close:
               if current_rsi < 40:
                return self.BUY

        if current_psar > current_close:

            if current_rsi > 60:
                return self.SELL




        return self.NONE

    def _rsi_trainer(self, version: str):

        json_objs = []
        for rsi_upper, rsi_lower, trend in itertools.product(list(range(55, 80, 3)), list(range(20, 45, 3)),
                                                             [None, .005, .01, .03, .05]):
            json_objs.append({
                "rsi_upper_limit": rsi_upper,
                "rsi_lowe_limit": rsi_lower,
                "rsi_trend": trend,
                "version": version
            })
        return json_objs

    def _BB_trainer(self, version: str):

        json_objs = []
        for p1, p2, peaks in itertools.product(
                list(range(1, 5)),
                list(range(1, 5)),
                list(range(0, 4))):
            json_objs.append({
                "period_1": p1,
                "period_2": p2,
                "peak_count": peaks,
                "version": version
            })
        return json_objs

    def _BB_change_trainer(self, version: str):

        json_objs = []
        for change in [None, 0.1, 0.3, .5, .7, 1.0]:
            json_objs.append({
                "bb_change": change,
                "version": version
            })
        return json_objs

    def get_training_sets(self, version: str):

        bb1 = self._BB_trainer(version)
        bb2 = self._BB_change_trainer(version)
        sl = self._stop_limit_trainer(version)

        return bb1 + bb2 + sl

