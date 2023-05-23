import os.path
import json
from Predictors.base_predictor import BasePredictor
from pandas import DataFrame, Series
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer
from BL.candle import MultiCandle, MultiCandleType


class Reversal(BasePredictor):

    # https://www.youtube.com/watch?v=6c5exPYoz3U
    rsi_upper_limit = 75
    rsi_lower_limit = 25
    period_1 = 2
    period_2 = 3
    peak_count = 0
    rsi_trend = 0.05
    bb_change = None

    def __init__(self, config=None, tracer: Tracer = ConsoleTracer()):
        super().__init__(config, tracer)
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

    def predict(self, df: DataFrame) -> str:
        if len(df) < 10:
            return BasePredictor.NONE


        rsi = df.tail(1).RSI.values[0]
        p1 = self.period_1 * -1
        break_period = df[p1:]
        down_breaks = len(break_period[break_period.low < break_period.BB_LOWER]) > self.peak_count
        up_breaks = len(break_period[break_period.high > break_period.BB_UPPER]) > self.peak_count

        down_breaks = up_breaks = True

        mc  = MultiCandle(df)
        candle_pattern = mc.get_type()

        steigung = self.calc_trend(df, 4)

        # buy
        #if rsi < self.rsi_lower_limit and \
        if down_breaks and steigung == -1:
            if candle_pattern in [MultiCandleType.MorningStart,MultiCandleType.BullishEngulfing,MultiCandleType.ThreeWhiteSoldiers]:
                return BasePredictor.BUY

        #if rsi > self.rsi_upper_limit \
        if up_breaks and steigung == 1:
            if candle_pattern in [MultiCandleType.EveningStar, MultiCandleType.BearishEngulfing,
                                  MultiCandleType.ThreeBlackCrows]:
                return BasePredictor.SELL



        return self.NONE