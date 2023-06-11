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


class LevelSection:

    def __init__(self, level, diff):
        self.upper = level + diff
        self.middle = level
        self.lower = level - diff


class SRCandleRsi(BasePredictor):
    # https://www.youtube.com/watch?v=6c5exPYoz3U
    period_1 = 2
    period_2 = 3
    zig_zag_percent = 0.5
    merge_percent = 0.1
    min_bars_between_peaks = 20
    look_back_days = 20
    level_section_size = 1.0
    rsi_upper = 60
    rsi_lower = 40

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
                       self.last_scan
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
                             "last_scan"])





    def get_levels(self, df):
        look_back = df[self.look_back_days * 24 * -1:]
        zl = ZigZagClusterLevels(peak_percent_delta=self.zig_zag_percent, merge_distance=None,
                                 merge_percent=self.merge_percent, min_bars_between_peaks=self.min_bars_between_peaks, peaks='Low')
        zl.fit(look_back)

        levels = []
        if zl.levels != None:
            for l in zl.levels:
                levels.append(l["price"])
            levels.sort()

        level_sections = []
        current_mean_range = self.get_mean_range(df)

        for l in levels:
            level_sections.append(LevelSection(l, current_mean_range * self.level_section_size))

        return level_sections

    def _level_check(self,df):
        levels = self.get_levels(df)

        if len(levels) == 0:
            return BasePredictor.NONE

        current_close = df.tail(1).close.values[0]

        for i in range(len(levels)):
            l = levels[i]
            if df.index[-1] % 10 == 0:
                self._viewer.print_level(df[-7:-6].date.values[0], df[-1:].date.values[0], l.upper, l.lower)

            p1 = df[-2:-1]
            p2 = df[-10:-2]

            # buy
            if current_close > l.upper:
                was_under = len(p1[p1.low < l.upper]) > 0
                was_over = len(p2[p2.close > l.middle]) > 5

                if was_over and was_under:
                    self._viewer.print_level(df[-7:-6].date.values[0], df[-1:].date.values[0], l.upper, l.lower, "Red")
                    return self.BUY

            if current_close < l.lower:
                was_over = len(p1[p1.high > l.lower]) > 0
                was_under = len(p2[p2.close < l.middle]) > 5

                if was_over and was_under:
                    self._viewer.print_level(df[-7:-6].date.values[0], df[-1:].date.values[0], l.upper, l.lower, "Red")
                    return self.SELL

        return self.NONE

    def predict(self, df: DataFrame) -> str:
        if len(df) < 150:
            return BasePredictor.NONE



        mc = MultiCandle(df)
        current_rsi = df.tail(1).RSI.values[0]
        mean_range = self.get_mean_range(df)

        type =  mc.get_type()
        if type == MultiCandleType.MorningStart or \
            type == MultiCandleType.BullishEngulfing:
                if self._level_check(df) == self.BUY:
                    if current_rsi < self.rsi_upper:
                        return self.BUY



        if type == MultiCandleType.EveningStar or \
            type == MultiCandleType.BearishEngulfing:
                if self._level_check(df) == self.SELL:
                    if current_rsi > self.rsi_lower:
                        return self.SELL





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
        for upper, lower in itertools.product([50,55,60,65], [35,40,45]):
            json_objs.append({
                "rsi_upper": upper,
                "rsi_lower": lower,
                "version": version
            })
        return json_objs

    @staticmethod
    def get_training_sets(version:str):

        sr1 = SRCandleRsi._sr_trainer(version)
        sr2 = SRCandleRsi._sr_trainer2(version)
        sl = BasePredictor._stop_limit_trainer(version)
        rsi = SRCandleRsi._rsi_trainer(version)

        return sr1 + sr2 + rsi + sl

