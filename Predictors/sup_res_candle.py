import os.path
import json

from BL.pricelevels import ZigZagClusterLevels
from Predictors.base_predictor import BasePredictor
from pandas import DataFrame, Series
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer
from BL.candle import MultiCandle, MultiCandleType, Candle, CandleType, Direction
from UI.base_viewer import BaseViewer
import numpy as np

class LevelSection:

    def __init__(self, level, diff):
        self.upper = level + diff
        self.lower = level - diff


class SupResCandle(BasePredictor):

    # https://www.youtube.com/watch?v=6c5exPYoz3U
    rsi_upper_limit = 75
    rsi_lower_limit = 25
    period_1 = 2
    period_2 = 3
    zig_zag_percent = 0.5


    def __init__(self, config=None, tracer: Tracer = ConsoleTracer(),viewer:BaseViewer = BaseViewer()):
        super().__init__(config, tracer)
        if config is None:
            config = {}
        self.setup(config)
        self._viewer = viewer

    def setup(self, config: dict):
        self.rsi_upper_limit = config.get("rsi_upper_limit", self.rsi_upper_limit)
        self.rsi_lower_limit = config.get("rsi_lower_limit", self.rsi_lower_limit)
        self.period_1 = config.get("period_1", self.period_1)
        self.period_2 = config.get("period_2", self.period_2)
        super().setup(config)

    def get_config(self) -> Series:
        return Series(["RSI_BB",
                       self.stop,
                       self.limit,
                       self.rsi_upper_limit,
                       self.rsi_lower_limit,
                       self.period_1,
                       self.period_2,
                       self.version,
                       self.best_result,
                       self.best_reward,
                       self.frequence
                       ],
                      index=["Type", "stop", "limit", "rsi_upper_limit",
                             "rsi_lower_limit", "period_1", "period_2", "version","best_result","best_reward","frequence"])

    def save(self, symbol: str):
        self.get_config().to_json(self._get_save_path(self.__class__.__name__, symbol))

    def saved(self, symbol):
        return os.path.exists(self._get_save_path(self.__class__.__name__, symbol))

    def load(self, symbol: str):
        if self.saved(symbol):
            with open(self._get_save_path(self.__class__.__name__, symbol)) as json_file:
                data = json.load(json_file)
                self.setup(data)
        else:
            self._tracer.debug(f"No saved settings of {symbol}")
        return self

    def _get_levels(self,df):
        zl = ZigZagClusterLevels(peak_percent_delta=self.zig_zag_percent, merge_distance=None,
                                 merge_percent=0.1, min_bars_between_peaks=20, peaks='Low')
        zl.fit(df)

        levels = []
        if zl.levels != None:
            for l in zl.levels:
                levels.append(l["price"])
            levels.sort()
        return levels

    def predict(self, df: DataFrame) -> str:
        if len(df) < 150:
            return BasePredictor.NONE

        levels = self._get_levels(df)

        if len(levels) == 0:
            return BasePredictor.NONE

        mc = MultiCandle(df)
        c = Candle(df[-1:])
        candle_dir = c.direction()
        candle_size = c.get_body_percentage()
        current_close = df.tail(1).close.values[0]

        current_mean_range = self.get_mean_range(df)

        for i in range(len(levels)):
            l = levels[i]
            if df.index[-1] % 10 == 0:
                self._viewer.print_level(df[-4:-3].date.values[0], df[-1:].date.values[0], l)

            diff_to_next_level = 1000
            if current_close < l: #Price under level
                if i != 0:
                    diff_to_next_level = abs(levels[i - 1] - current_close)
            else: #Price over level
                if i < len(levels) - 1:
                    diff_to_next_level = abs(levels[i + 1] - current_close)


            #price should not to far from level
            diff_to_curent_level = abs(l - current_close)
            if diff_to_curent_level > current_mean_range * 4:
                continue

            #Close to current lebel
            if diff_to_curent_level > diff_to_next_level * 0.25:
                continue

            p1 = df[-2:-1]
            p2 = df[-10:-2]

            # buy
            if current_close > l:
                was_under = len(p1[p1.low < l]) > 0
                was_over = len(p2[p2.close > l]) > 5

                if was_over and was_under:
                        self._viewer.print_level(df[-4:-3].date.values[0], df[-1:].date.values[0], l,"Red")
                        return self.BUY

            if current_close < l:
                was_over = len(p1[p1.high > l]) > 5
                was_under = len(p2[p2.close < l]) > 0

                if was_over and was_under:
                        self._viewer.print_level(df[-4:-3].date.values[0], df[-1:].date.values[0], l, "Red")
                        return self.SELL

            p1 = df[-10:]
            if len(p1[p1.close < l]) == 0:
                if candle_dir == Direction.Bullish and candle_size > 60:
                    if len(p1[abs(p1.low - l) < current_mean_range]) > 0:
                            self._viewer.print_level(df[-4:-3].date.values[0], df[-1:].date.values[0], l ,"Red")
                            return self.BUY

            if len(p1[p1.close > l]) == 0:
                if candle_dir == Direction.Bearish and candle_size > 60:
                    if len(p1[abs(p1.low - l) < current_mean_range]) > 0:
                            self._viewer.print_level(df[-4:-3].date.values[0], df[-1:].date.values[0], l, "Red")
                            return self.SELL

        return self.NONE
