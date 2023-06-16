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
    period_1 = 2
    period_2 = 3
    zig_zag_percent = 0.5
    merge_percent = 0.1
    min_bars_between_peaks = 20
    look_back_days = 20
    level_section_size = 1.0
    rsi_buy_limit = 35
    rsi_sell_limit = 65
    rsi_type = "RSI"

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
        self.period_1 = config.get("period_1", self.period_1)
        self.period_2 = config.get("period_2", self.period_2)
        self.zig_zag_percent = config.get("zig_zag_percent", self.zig_zag_percent)
        self.merge_percent = config.get("merge_percent", self.merge_percent)
        self.min_bars_between_peaks = config.get("min_bars_between_peaks", self.min_bars_between_peaks)
        self.look_back_days = config.get("look_back_days", self.look_back_days)
        self.level_section_size = config.get("level_section_size", self.level_section_size)
        self.rsi_buy_limit = config.get("rsi_buy_limit", self.rsi_buy_limit)
        self.rsi_sell_limit = config.get("rsi_sell_limit", self.rsi_sell_limit)
        self.rsi_type = config.get("rsi_type", self.rsi_type)

        super().setup(config)

    def get_config(self) -> Series:
        return Series(["SupResCandle",
                       self.stop,
                       self.limit,
                       self.period_1,
                       self.period_2,
                       self.zig_zag_percent,
                       self.merge_percent,
                       self.min_bars_between_peaks,
                       self.look_back_days,
                       self.level_section_size,
                       self.version,
                       self.best_result,
                       self.best_reward,
                       self.trades,
                       self.frequence,
                       self.last_scan,
                       self.rsi_buy_limit,
                       self.rsi_sell_limit,
                       self.rsi_type
                       ],
                      index=["Type",
                             "stop",
                             "limit",
                             "period_1",
                             "period_2",
                             "zig_zag_percent",
                             "merge_percent",
                             "min_bars_between_peaks",
                             "look_back_days",
                             "level_section_size",
                             "version",
                             "best_result",
                             "best_reward",
                             "trades",
                             "frequence",
                             "last_scan",
                             "rsi_buy_limit",
                             "rsi_sell_limit",
                             "rsi_type"])


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

        if current_stochd < 50 and current_stochd > 35 and pret_stochd > current_stochd:
            if current_close < current_ema:
                return self.SELL

        if current_stochd > 50 and current_stochd < 65 and pret_stochd < current_stochd:
            if current_close > current_ema:
                return self.BUY



    @staticmethod
    def _sr_trainer(version: str):

        json_objs = []
        for zig_zag_percent, merge_percent, min_bars_between_peaks in itertools.product([.3, .4, .5, .7, .9],
                                                                                        [0.05, 0.1, .2, .3],
                                                                                        [17, 23, 27]):
            json_objs.append({
                "zig_zag_percent": zig_zag_percent,
                "merge_percent": merge_percent,
                "min_bars_between_peaks": min_bars_between_peaks,
                "version": version
            })
        return json_objs

    @staticmethod
    def _sr_trainer2(version: str):

        json_objs = []
        for look_back_days, level_section_size in itertools.product([13, 17, 21, 24], [0.7, 1.0, 1.3, 1.7]):
            json_objs.append({
                "look_back_days": look_back_days,
                "level_section_size": level_section_size,
                "version": version
            })
        return json_objs

    @staticmethod
    def _rsi_trainer(version: str):

        json_objs = []
        for buy, sell,type in itertools.product([30,37,44,50],[50,57,64,70],["RSI","RSI_9"]):
            json_objs.append({
                "rsi_buy_limit": buy,
                "rsi_sell_limit": sell,
                "rsi_type":type,
                "version": version
            })
        return json_objs

    @staticmethod
    def get_training_sets(version:str):

        sr1 = SRCandleRsi._sr_trainer(version)
        sr2 = SRCandleRsi._sr_trainer2(version)
        sl = BasePredictor._stop_limit_trainer(version)
        rsi = SRCandleRsi._rsi_trainer(version)

        #return rsi
        return sr1 + sr2 + rsi + sl

