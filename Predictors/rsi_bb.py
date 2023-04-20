import os.path
import json
from Predictors.base_predictor import BasePredictor
from pandas import DataFrame, Series


class RsiBB(BasePredictor):
    # https://www.youtube.com/watch?v=6c5exPYoz3U
    upper_limit = 80
    lower_limit = 20
    rsi_upper_limit = 80
    rsi_lower_limit = 23
    period_1 = 5

    def __init__(self, config=None):
        super().__init__(config)
        if config is None:
            config = {}
        self.setup(config)

    def setup(self, config: dict):
        self.upper_limit = config.get("upper_limit", self.upper_limit)
        self.lower_limit = config.get("lower_limit", self.lower_limit)
        self.rsi_upper_limit = config.get("rsi_upper_limit", self.rsi_upper_limit)
        self.rsi_lower_limit = config.get("rsi_lower_limit", self.rsi_lower_limit)
        self.period_1 = config.get("period_1", self.period_1)
        self.limit = config.get("limit", self.limit)
        self.stop = config.get("stop", self.stop)

    def get_config(self) -> Series:
        return Series(["RSI_BB",
                       self.stop,
                       self.limit,
                       self.rsi_upper_limit,
                       self.rsi_lower_limit,
                       self.period_1],
                      index=["Type", "stop", "limit", "rsi_upper_limit",
                             "rsi_lower_limit", "period_1"])

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

    def predict(self, df: DataFrame) -> str:
        if len(df) == 0:
            return BasePredictor.NONE

        if len(df) > self.period_1:
            rsi = df.tail(1).RSI.values[0]
            p1 = self.period_1 * -1
            down_breaks = len(df[p1:][df.low < df.BB_LOWER]) > 0
            up_breaks = len(df[p1:][df.high > df.BB_UPPER]) > 0

            # buy
            if rsi < self.rsi_lower_limit and down_breaks:
                return BasePredictor.BUY

            if rsi > self.rsi_upper_limit and up_breaks:
                return BasePredictor.SELL

        return self.NONE
