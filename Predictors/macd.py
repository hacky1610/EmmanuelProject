import os.path
import json
from Predictors.base_predictor import BasePredictor
from pandas import DataFrame, Series
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer


class MACD(BasePredictor):

    # https://www.youtube.com/watch?v=6c5exPYoz3U
    rsi_upper_limit = 80
    rsi_lower_limit = 23
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

        current_macd_periode = df[-3:]
        macd_over_signal = len(current_macd_periode[current_macd_periode.MACD > current_macd_periode.SIGNAL]) == 3
        macd_under_signal = len(current_macd_periode[current_macd_periode.MACD < current_macd_periode.SIGNAL]) == 3


        trend_periode = df[-10:]

        pre_macd = df.tail(3).MACD.values[0]
        pre_signal = df.tail(3).SIGNAL.values[0]
        current_close = df.tail(1).close.values[0]
        current_ema= df.tail(1).EMA_150.values[0]

        #buy

        if macd_over_signal:
            if current_close > current_ema:
                d = current_macd_periode.MACD - current_macd_periode.SIGNAL
                if d.diff().values[1] > 0 and d.diff().values[2] > 0 and \
                    self.interpret_candle(df[-1:]) == self.BUY:
                    return BasePredictor.BUY


        if macd_under_signal:
            if current_close < current_ema:
                d = current_macd_periode.SIGNAL - current_macd_periode.MACD
                if d.diff().values[1] > 0 and d.diff().values[2] > 0 and \
                        self.interpret_candle(df[-1:]) == self.BUY:
                    return BasePredictor.SELL

        return BasePredictor.NONE
