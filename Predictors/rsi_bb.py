import os.path
import json
from Predictors.base_predictor import BasePredictor
from pandas import DataFrame, Series
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer


class RsiBB(BasePredictor):
    # https://www.youtube.com/watch?v=6c5exPYoz3U
    rsi_upper_limit = 80
    rsi_lower_limit = 23
    period_1 = 2
    period_2 = 3
    peak_count = 0
    rsi_trend = 0.05

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
        self.limit = config.get("limit", self.limit)
        self.stop = config.get("stop", self.stop)
        self.rsi_trend = config.get("rsi_trend", self.rsi_trend)

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
                       self.version
                       ],
                      index=["Type", "stop", "limit", "rsi_upper_limit",
                             "rsi_lower_limit", "period_1", "period_2", "peak_count", "rsi_trend","version"])

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
        if len(df) == 0:
            return BasePredictor.NONE

        if len(df) > (self.period_1 + self.period_2):
            rsi = df.tail(1).RSI.values[0]
            p1 = self.period_1 * -1
            p2 = (self.period_1 + self.period_2) * -1
            break_period = df[p1:]
            down_breaks = len(break_period[break_period.low < break_period.BB_LOWER]) > self.peak_count
            up_breaks = len(break_period[break_period.high > break_period.BB_UPPER]) > self.peak_count

            no_break_period = df[p2:p1]
            no_down_breaks = len(no_break_period[no_break_period.low < no_break_period.BB_LOWER]) == 0
            no_up_breaks = len(no_break_period[no_break_period.high > no_break_period.BB_UPPER]) == 0

            rsi_trend = df.RSI.pct_change(1).tail(1).values[0]

            # buy
            if rsi < self.rsi_lower_limit and \
                    down_breaks and \
                    no_down_breaks and \
                    rsi_trend < self.rsi_trend * -1:
                self._tracer.write(f"Buy - Time: {df.tail(1).date.values[0]} \n\r"
                                   f"RSI: {rsi} RSI LL: {self.rsi_lower_limit} \n\r"
                                   f"P2: {no_break_period.filter(['date', 'low', 'BB_LOWER', 'RSI'])} \n\r"
                                   f"P1: {break_period.filter(['date', 'low', 'BB_LOWER', 'RSI'])} \n\r"
                                   f"len {len(df)}\n\r"
                                   f"RSI trend {rsi_trend} - Max trend {self.rsi_trend * -1} \n\r"
                                   )
                return BasePredictor.BUY

            if rsi > self.rsi_upper_limit \
                    and up_breaks \
                    and no_up_breaks \
                    and rsi_trend > self.rsi_trend:
                self._tracer.write(f"Sell - Time: {df.tail(1).date.values[0]} \n\r"
                                   f"RSI: {rsi} RSI UL: {self.rsi_upper_limit} \n\r"
                                   f"P2: {no_break_period.filter(['date', 'high', 'BB_UPPER', 'RSI'])} \n\r"
                                   f"P1: {break_period.filter(['date', 'high', 'BB_UPPER', 'RSI'])} \n\r"
                                   f"len {len(df)}\n\r"
                                   f"RSI trend {rsi_trend} - Min trend {self.rsi_trend} \n\r"
                                   )

                return BasePredictor.SELL

            self._tracer.write(f"No Action - Time: {df.tail(1).date.values[0]} \n\r"
                               f"RSI: {rsi} RSI UL: {self.rsi_upper_limit} RSI UL: {self.rsi_lower_limit} \n\r"
                               f"P2: {no_break_period.filter(['date', 'low', 'BB_LOWER', 'high', 'BB_UPPER', 'RSI'])} \n\r"
                               f"P1: {break_period.filter(['date', 'low', 'BB_LOWER', 'high', 'BB_UPPER', 'RSI'])} \n\r"
                               f"len {len(df)}\n\r"
                               f"RSI trend {rsi_trend} - Defined trend {self.rsi_trend} \n\r"
                               )

        return self.NONE
