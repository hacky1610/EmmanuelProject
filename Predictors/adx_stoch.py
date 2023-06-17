import itertools
import os.path
import json

from BL.pricelevels import ZigZagClusterLevels
from Connectors import BaseCache
from Predictors.base_predictor import BasePredictor
from pandas import DataFrame, Series
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer
from BL.candle import MultiCandle, MultiCandleType, Candle, CandleType, Direction
from UI.base_viewer import BaseViewer
import numpy as np
from datetime import  datetime



class ADXSTOCH(BasePredictor):
    # https://www.youtube.com/watch?v=6c5exPYoz3U
    buy_stoch_max = 65
    buy_stoch_min = 50
    sell_stoch_max = 50
    sell_stoch_min = 35

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


        super().setup(config)

    def get_config(self) -> Series:
        return Series(["SupResCandle",
                       self.stop,
                       self.limit,
                       self.sell_stoch_min,
                       self.sell_stoch_max,
                       self.buy_stoch_min,
                       self.buy_stoch_max,
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
                             "version",
                             "best_result",
                             "best_reward",
                             "trades",
                             "frequence",
                             "last_scan",
                             ])


    def predict(self, df: DataFrame) -> str:
        if len(df) < 15:
            return BasePredictor.NONE


        current_stochd = df["STOCHD_21"][-1:].item()
        pret_stochd = df["STOCHD_21"][-2:-1].item()
        current_adx = df["ADX"][-1:].item()
        current_ema = df["EMA_20"][-1:].item()
        current_close = df["close"][-1:].item()
        pret_adx = df["ADX"][-2:-1].item()

        if current_adx < pret_adx:
            return self.NONE

        if current_stochd < self.sell_stoch_max and current_stochd > self.sell_stoch_min and pret_stochd > current_stochd:
            if current_close < current_ema:
                return self.SELL

        if current_stochd > self.buy_stoch_min and current_stochd < self.buy_stoch_max and pret_stochd < current_stochd:
            if current_close > current_ema:
                return self.BUY



    @staticmethod
    def _stoch_trainer(version: str):

        json_objs = []
        for buy_max, buy_min, sell_min, sell_max in itertools.product(
                range(50,70,5),
                range(45,55,5),
                range(45,55,5),
                range(30,50,5)):
            json_objs.append({
                "buy_stoch_max": buy_max,
                "buy_stoch_min": buy_min,
                "sell_stoch_max": sell_max,
                "sell_stoch_min": sell_min,
                "version": version
            })
        return json_objs





    @staticmethod
    def get_training_sets(version:str):

        stoch = ADXSTOCH._stoch_trainer(version)

        return stoch


