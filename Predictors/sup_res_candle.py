import os.path
import json

from BL.pricelevels import ZigZagClusterLevels
from Predictors.base_predictor import BasePredictor
from pandas import DataFrame, Series
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer
from BL.candle import MultiCandle, MultiCandleType, Candle, CandleType
from UI.base_viewer import BaseViewer


class SupResCandle(BasePredictor):

    # https://www.youtube.com/watch?v=6c5exPYoz3U
    rsi_upper_limit = 75
    rsi_lower_limit = 25
    period_1 = 2
    period_2 = 3
    zig_zag_percent = 0.8


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

    def predict(self, df: DataFrame) -> str:
        if len(df) < 150:
            return BasePredictor.NONE

        zl = ZigZagClusterLevels(peak_percent_delta=self.zig_zag_percent, merge_distance=None,
                                 merge_percent=0.1, min_bars_between_peaks=20, peaks='Low')
        zl.fit(df)
        if zl.levels is None:
            return BasePredictor.NONE

        mc = MultiCandle(df)
        candle_pattern = mc.get_type()
        candle_type = Candle(df[-1:]).candle_type()
        low = df.tail(1).low.values[0]
        high = df.tail(1).low.values[0]

        for l in zl.levels:



            p1 = df[-2:]
            p2 = df[-10:-2]


            # buy
            under = len(p1[p1.close < l["price"]]) > 0
            was_over = len(p2[p2.close > l["price"]]) > 5

            if under and was_over:
                if candle_pattern in [MultiCandleType.BullishEngulfing, MultiCandleType.MorningStart]:
                    self._viewer.print_level(df[-4:-3].date.values[0],df[-1:].date.values[0], l["price"])
                    return BasePredictor.BUY

            #sell
            over = len(p1[p1.close > l["price"]]) > 0
            was_under = len(p2[p2.close < l["price"]]) > 5

            if over and was_under:
                if candle_pattern in [MultiCandleType.BearishEngulfing,MultiCandleType.EveningStar]:
                    self._viewer.print_level(df[-4:-3].date.values[0],df[-1:].date.values[0],  l["price"])
                    return BasePredictor.SELL


        return self.NONE
