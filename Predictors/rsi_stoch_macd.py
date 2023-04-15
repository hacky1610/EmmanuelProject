from Predictors import BasePredictor
from pandas import DataFrame,Series

class RsiStochMacd(BasePredictor):
    #https://www.youtube.com/watch?v=6c5exPYoz3U
    upper_limit = 80
    lower_limit = 20
    rsi_upper_limit = 83
    rsi_lower_limit = 25
    period_1 = 3
    diff_factor = 0.7

    _settings = {
        "default": {
            "period_1": 15,
            "period_2": 15,
            "stop": 2.0,
            "limit": 1.0
        },
        "EURUSD": {
            "period_1": 18,
            "period_2": 21,
            "stop": 2.5,
            "limit": 3.5
        },
        "EURGBP": {
            "period_1": 18,
            "period_2": 21,
            "stop": 2.5,
            "limit": 3.5
        },
        "USDJPY": {
            "period_1": 15,
            "period_2": 24,
            "stop": 1.5,
            "limit": 1.8
        },
        "EURCHF": {
            "period_1": 15,
            "period_2": 24,
            "stop": 2.8,
            "limit": 1.8
        },
        "GBPUSD": {
            "period_1": 18,
            "period_2": 18,
            "stop": 2.5,
            "limit": 2.1
        },
        "AUDUSD": {
            "period_1": 15,
            "period_2": 15,
            "stop": 2.0,
            "limit": 1.0
        },
        "EURJPY": {
            "period_1": 15,
            "period_2": 15,
            "stop": 2.5,
            "limit": 2.5
        },
        "AUDJPY": {
            "period_1": 21,
            "period_2": 15,
            "stop": 1.5,
            "limit": 1.5
        },
        "CHFJPY": {
            "period_1": 15,
            "period_2": 15,
            "stop": 2.0,
            "limit": 1.0
        },
        "EURAUD": {
            "period_1": 15,
            "period_2": 15,
            "stop": 2.0,
            "limit": 1.0
        },
        "EURSGD": {
            "period_1": 15,
            "period_2": 18,
            "stop": 1.8,
            "limit": 1.8
        },
        "GBPJPY": {
            "period_1": 21,
            "period_2": 24,
            "stop": 2.5,
            "limit": 1.8
        }
    }

    def __init__(self, config: dict):
        super().__init__(config)
        self.upper_limit = config.get("upper_limit", self.upper_limit)
        self.lower_limit = config.get("lower_limit", self.lower_limit)
        self.rsi_upper_limit = config.get("rsi_upper_limit", self.rsi_upper_limit)
        self.rsi_lower_limit = config.get("rsi_lower_limit", self.rsi_lower_limit)
        self.period_1 = config.get("period_1", self.period_1)
        self.limit = config.get("limit", self.limit)
        self.stop = config.get("stop", self.stop)
        self.diff_factor = config.get("diff_factor", self.diff_factor)

    def get_config(self) -> str:
        #stop, limit = self.get_stop_limit()
        return f"Stop *: {self.stop} " \
               f"Limit *: {self.limit} " \
               f"U-Limit: {self.upper_limit} " \
               f"L-Limit: {self.lower_limit} " \
               f"RSI-U-Limit: {self.rsi_upper_limit} " \
               f"RSI-L-Limit: {self.rsi_lower_limit} " \
               f"P1: {self.period_1} " \

    def predict(self,df:DataFrame) -> str:
        p1 = self.period_1 * -1
        sd = df.tail(1).STOCHD.values[0]
        sk = df.tail(1).STOCHK.values[0]
        rsi = df.tail(1).RSI.values[0]
        df["MACD_DIFF"] = df.MACD - df.SIGNAL
        macd_diff = df.tail(1).MACD_DIFF.values[0]
        pos_mean = (df[df.MACD_DIFF > 0].MACD_DIFF.mean()) * self.diff_factor
        neg_mean = (abs(df[df.MACD_DIFF < 0].MACD_DIFF.mean())) * self.diff_factor

        if (len(df) > abs(p1)):

            if rsi < 50  and macd_diff > neg_mean:
                return self.BUY

            #Sell
            if rsi > 50 and  macd_diff > pos_mean:
                return self.SELL

        return self.NONE

    def get_settings(self, ticker: str):
        return self._settings.get(ticker, self._settings["default"])

    def set_config(self, ticker: str):
        settings = self.get_settings(ticker)

        self.stop = settings["stop"]
        self.limit = settings["limit"]
        self.period_1 = settings["period_1"]
        self.period_2 = settings["period_2"]

    def get_config_as_string(self) -> str:
        # stop, limit = self.get_stop_limit()
        return f"Stop *: {self.stop} " \
               f"Limit *: {self.limit} " \
               f"U-Limit: {self.upper_limit} " \
               f"L-Limit: {self.lower_limit} " \
               f"RSI-U-Limit: {self.rsi_upper_limit} " \
               f"RSI-L-Limit: {self.rsi_lower_limit} " \
               f"P1: {self.period_1} " \
               f"Factor: {self.diff_factor} "

    def get_config(self) -> Series:
        return Series(["RSI_Stoch",
                       self.stop,
                       self.limit,
                       self.upper_limit,
                       self.lower_limit,
                       self.rsi_upper_limit,
                       self.rsi_lower_limit,
                       self.period_1,
                       self.diff_factor],
                      index=["Type", "Stop", "Limit", "Upper Limit", "Lower Limit", "RSI Upper Limit",
                             "RSI Lower Limit", "Period", "Diff Factor"])




