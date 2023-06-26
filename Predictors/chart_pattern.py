import itertools
import os.path
import json

from BL.chart_pattern import ChartPattern, PatternType
from BL.pricelevels import ZigZagClusterLevels
from Connectors import BaseCache
from Predictors.base_predictor import BasePredictor
from pandas import DataFrame, Series
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer
from BL.candle import MultiCandle, MultiCandleType, Candle, CandleType, Direction
from UI.base_viewer import BaseViewer
import numpy as np
from datetime import datetime


class ChartPatternPredictor(BasePredictor):
    # https://www.youtube.com/watch?v=6c5exPYoz3U
    buy_stoch_max = 65
    buy_stoch_min = 50
    sell_stoch_max = 50
    sell_stoch_min = 35
    adx_max = 50
    adx_min = 10
    adx_diff_min = 2

    def __init__(self, config=None,
                 tracer: Tracer = ConsoleTracer(),
                 viewer: BaseViewer = BaseViewer(),
                 cache: BaseCache = BaseCache()):
        super().__init__(config, tracer=tracer, cache=cache)
        if config is None:
            config = {}
        self.setup(config)
        self._viewer = viewer

    def setup(self, config: dict):
        self.buy_stoch_max = config.get("buy_stoch_max", self.buy_stoch_max)
        self.buy_stoch_min = config.get("buy_stoch_min", self.buy_stoch_min)
        self.sell_stoch_max = config.get("sell_stoch_max", self.sell_stoch_max)
        self.sell_stoch_min = config.get("sell_stoch_min", self.sell_stoch_min)
        self.adx_min = config.get("adx_min", self.adx_min)
        self.adx_max = config.get("adx_max", self.adx_max)
        self.adx_max = config.get("adx_diff_min", self.adx_diff_min)

        super().setup(config)

    def get_config(self) -> Series:
        return Series(["SupResCandle",
                       self.stop,
                       self.limit,
                       self.sell_stoch_min,
                       self.sell_stoch_max,
                       self.buy_stoch_min,
                       self.buy_stoch_max,
                       self.adx_min,
                       self.adx_max,
                       self.adx_diff_min,
                       self.version,
                       self.best_result,
                       self.best_reward,
                       self.trades,
                       self.frequence,
                       self.last_scan,
                       ],
                      index=["Type",
                             "stop",
                             "limit",
                             "sell_stoch_min",
                             "sell_stoch_max",
                             "buy_stoch_min",
                             "buy_stoch_max",
                             "adx_min",
                             "adx_max",
                             "adx_diff_min",
                             "version",
                             "best_result",
                             "best_reward",
                             "trades",
                             "frequence",
                             "last_scan",
                             ])

    def predict(self, df: DataFrame):
        #if len(df) < 15:
        return BasePredictor.NONE,0,0

        cp = ChartPattern()
        res = cp.get_pattern(df)

        if res == PatternType.DoubleTop:
            return self.SELL, 0, 0

        return self.NONE,0,0

    @staticmethod
    def _stoch_buy_trainer(version: str):

        json_objs = []
        for buy_max, buy_min in itertools.product(
                range(50, 70, 5),
                range(45, 55, 5),
        ):
            json_objs.append({
                "buy_stoch_max": buy_max,
                "buy_stoch_min": buy_min,
                "version": version
            })
        return json_objs

    @staticmethod
    def _stoch_sell_trainer(version: str):

        json_objs = []
        for sell_min, sell_max in itertools.product(
                range(45, 55, 5),
                range(30, 50, 5)):
            json_objs.append({
                "sell_stoch_max": sell_max,
                "sell_stoch_min": sell_min,
                "version": version
            })
        return json_objs

    def _adx_max_trainer(version: str):

        json_objs = []
        for adx in range(20, 50, 3):
            json_objs.append({
                "adx_max": adx,
                "version": version
            })
        return json_objs

    def _adx_min_trainer(version: str):

        json_objs = []
        for adx in range(10, 25, 3):
            json_objs.append({
                "adx_min": adx,
                "version": version
            })
        return json_objs

    def _adx_diff_trainer(version: str):

        json_objs = []
        for diff in [1.5, 2.0, 2.5, 4]:
            json_objs.append({
                "adx_diff_min": diff,
                "version": version
            })
        return json_objs

    @staticmethod
    def get_training_sets(version: str):
        return ADXSTOCH._stoch_buy_trainer(version) + \
            ADXSTOCH._stoch_sell_trainer(version) + \
            ADXSTOCH._adx_diff_trainer(version)
            #ADXSTOCH._adx_min_trainer(version) + \
            #ADXSTOCH._adx_max_trainer(version) + \

