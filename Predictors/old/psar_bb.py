import os.path
import json
from Predictors.base_predictor import BasePredictor
from pandas import DataFrame, Series
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer


class PsarBb(BasePredictor):

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
        current_ema = df.EMA_200[-1:].item()
        current_psar = df.PSAR[-1:].item()
        current_rsi = df.RSI[-1:].item()

        pre_psar_period = df[-5:-1]
        psar_was_under = len(pre_psar_period[pre_psar_period.PSAR < pre_psar_period.close]) == len(pre_psar_period)
        psar_was_over = len(pre_psar_period[pre_psar_period.PSAR > pre_psar_period.close]) == len(pre_psar_period)

        break_period = df[-5:]
        down_breaks = len(break_period[break_period.low < break_period.BB_LOWER]) > self.peak_count
        up_breaks = len(break_period[break_period.high > break_period.BB_UPPER]) > self.peak_count

        #buy
        if down_breaks and current_psar < current_close and psar_was_over:
            if current_close > current_ema:
                    return BasePredictor.BUY

        if up_breaks and current_psar > current_close and psar_was_under:
            if current_close < current_ema:
                    return BasePredictor.SELL



        return self.NONE
