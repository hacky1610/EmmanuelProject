import os.path
import json
from platform import machine

from Predictors.base_predictor import BasePredictor
from pandas import DataFrame, Series
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer


class PsarMacdStoch(BasePredictor):

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
        self.rsi_upper_limit = 50  #config.get("rsi_upper_limit", self.rsi_upper_limit)
        self.rsi_lower_limit = 50 #config.get("rsi_lower_limit", self.rsi_lower_limit)
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

        current_close = df.close[-1:].item()
        current_psar = df.PSAR[-1:].item()
        current_stochk = df.STOCHK[-1:].item()
        current_stochd = df.STOCHD[-1:].item()

        macd_period = df[-2:]
        macd_over_signal = len(macd_period[macd_period.MACD > macd_period.SIGNAL]) == len(macd_period)
        macd_under_signal = len(macd_period[macd_period.MACD < macd_period.SIGNAL]) == len(macd_period)

        stoch_period = df[-4:]
        stochd_under = len(stoch_period[stoch_period.STOCHD < 30]) > 0
        stochd_over = len(stoch_period[stoch_period.STOCHD > 70]) > 0

        #buy
        if macd_over_signal and current_psar < current_close and stochd_under:
            macd_signal_diff = macd_period.MACD - macd_period.SIGNAL
            if macd_signal_diff.diff().values[1] > 0:
                return BasePredictor.BUY

        if macd_under_signal and current_psar > current_close and stochd_over:
            signal_macd_diff = macd_period.SIGNAL - macd_period.MACD
            if signal_macd_diff.diff().values[1] > 0:
                return BasePredictor.SELL



        return self.NONE
