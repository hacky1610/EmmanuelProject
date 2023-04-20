import os.path
import json

from Predictors.base_predictor import BasePredictor
from pandas import DataFrame, Series
from BL.utils import get_project_dir


class RsiStoch(BasePredictor):
    # https://www.youtube.com/watch?v=6c5exPYoz3U
    upper_limit = 80
    lower_limit = 20
    rsi_upper_limit = 80
    rsi_lower_limit = 23
    period_1 = 3
    stoch_peeks = 2

    def __init__(self, config=None):
        super().__init__(config)
        if config is None:
            config = {}
        self.setup(config)


    def setup(self, config:dict):
        self.upper_limit = config.get("upper_limit", self.upper_limit)
        self.lower_limit = config.get("lower_limit", self.lower_limit)
        self.rsi_upper_limit = config.get("rsi_upper_limit", self.rsi_upper_limit)
        self.rsi_lower_limit = config.get("rsi_lower_limit", self.rsi_lower_limit)
        self.period_1 = config.get("period_1", self.period_1)
        self.stoch_peeks = config.get("stoch_peeks", self.stoch_peeks)
        self.limit = config.get("limit", self.limit)
        self.stop = config.get("stop", self.stop)

    def get_config_as_string(self) -> str:
        # stop, limit = self.get_stop_limit()
        return f"Stop *: {self.stop} " \
               f"Limit *: {self.limit} " \
               f"U-Limit: {self.upper_limit} " \
               f"L-Limit: {self.lower_limit} " \
               f"RSI-U-Limit: {self.rsi_upper_limit} " \
               f"RSI-L-Limit: {self.rsi_lower_limit} " \
               f"P1: {self.period_1} " \
               f"Peeks: {self.stoch_peeks} "

    def get_config(self) -> Series:
        return Series(["RSI_Stoch",
                       self.stop,
                       self.limit,
                       self.upper_limit,
                       self.lower_limit,
                       self.rsi_upper_limit,
                       self.rsi_lower_limit,
                       self.period_1,
                       self.stoch_peeks],
                      index=["Type", "stop", "limit", "upper_limit", "lower_limit", "rsi_upper_limit",
                             "rsi_lower_limit", "period_1", "stoch_peeks"])

    def save(self,symbol:str):
        self.get_config().to_json(self._get_save_path(symbol))

    def saved(self, symbol):
        return os.path.exists(self._get_save_path(symbol))

    def load(self,symbol:str):
        if self.saved(symbol):
            with open(self._get_save_path(symbol)) as json_file:
                data = json.load(json_file)
                self.setup(data)
        else:
            self._tracer.debug(f"No saved settings of {symbol}")

    def predict(self, df: DataFrame) -> str:
        if len(df) == 0:
            return BasePredictor.NONE

        p1 = self.period_1 * -1
        sd = df.tail(1).STOCHD.values[0]
        sk = df.tail(1).STOCHK.values[0]
        rsi = df.tail(1).RSI.values[0]

        if (len(df) > abs(p1)):

            if rsi < self.rsi_lower_limit and sd < self.upper_limit and sk < self.upper_limit:
                stoch_D_oversold = len(df[p1:][df.STOCHD < self.lower_limit]) >= self.stoch_peeks
                stoch_K_oversold = len(df[p1:][df.STOCHK < self.lower_limit]) >= self.stoch_peeks
                if stoch_D_oversold and stoch_K_oversold:
                    return self.BUY

            # Sell
            if rsi > self.rsi_upper_limit and sd > self.lower_limit and sk > self.lower_limit:
                stoch_D_overbought = len(df[p1:][df.STOCHD > self.upper_limit]) >= self.stoch_peeks
                stoch_K_overbought = len(df[p1:][df.STOCHK > self.upper_limit]) >= self.stoch_peeks
                if stoch_D_overbought and stoch_K_overbought:
                    return self.SELL

        return self.NONE



