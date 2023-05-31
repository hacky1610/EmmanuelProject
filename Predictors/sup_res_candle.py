from datetime import  datetime
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
        self.middle = level
        self.lower = level - diff


class SupResCandle(BasePredictor):
    # https://www.youtube.com/watch?v=6c5exPYoz3U
    period_1 = 2
    period_2 = 3
    zig_zag_percent = 0.5
    merge_percent = 0.1
    min_bars_between_peaks = 20
    look_back_days = 20
    level_section_size = 1.0

    def __init__(self, config=None, tracer: Tracer = ConsoleTracer(), viewer: BaseViewer = BaseViewer()):
        super().__init__(config, tracer)
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

    def save(self, symbol: str):
        self.last_scan = datetime.utcnow().isoformat()
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

    def _get_levels(self, df):
        zl = ZigZagClusterLevels(peak_percent_delta=self.zig_zag_percent, merge_distance=None,
                                 merge_percent=self.merge_percent, min_bars_between_peaks=self.min_bars_between_peaks, peaks='Low')
        zl.fit(df)

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

    def predict(self, df: DataFrame) -> str:
        if len(df) < 150:
            return BasePredictor.NONE

        levels = self._get_levels(df[self.look_back_days * 24 * -1:])

        if len(levels) == 0:
            return BasePredictor.NONE

        mc = MultiCandle(df)
        c = Candle(df[-1:])
        candle_dir = c.direction()
        candle_size = c.get_body_percentage()
        current_close = df.tail(1).close.values[0]
        current_open = df.tail(1).open.values[0]
        mean_range = self.get_mean_range(df)

        if mean_range * 3 < abs(current_open - current_close):
            return self.NONE

        for i in range(len(levels)):
            l = levels[i]
            if df.index[-1] % 10 == 0:
                self._viewer.print_level(df[-7:-6].date.values[0], df[-1:].date.values[0], l.upper, l.lower)

            diff_to_next_level = 1000
            if current_close < l.middle:  # Price under level
                if i != 0:
                    diff_to_next_level = abs(levels[i - 1].middle - current_close)
            else:  # Price over level
                if i < len(levels) - 1:
                    diff_to_next_level = abs(levels[i + 1].middle - current_close)

            diff_to_curent_level = abs(l.middle - current_close)

            # Close to current lebel
            if diff_to_curent_level > diff_to_next_level * 0.25:
                continue

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
