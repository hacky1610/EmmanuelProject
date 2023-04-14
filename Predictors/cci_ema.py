from pandas import DataFrame

from Predictors import CCI


class CCI_EMA(CCI):
    #https://www.youtube.com/watch?v=CuWzDo72-Rk
    upper_limit = 90
    lower_limit = -105
    period_1 = 24
    period_2 = 20

    _settings = {
        "default": {
            "upper_limit" : 90,
            "lower_limit" : -110,
            "period_1": 15,
            "period_2": 15,
            "stop" : 2.0,
            "limit" : 1.0
        },
        "EURUSD": {
            "upper_limit": 90,
            "lower_limit": -105,
            "period_1": 18,
            "period_2": 21,
            "stop": 2.5,
            "limit": 3.5
        },
        "EURGBP": {
            "upper_limit": 90,
            "lower_limit": -100,
            "period_1": 18,
            "period_2": 21,
            "stop": 2.5,
            "limit": 3.5
        },
        "USDJPY": {
            "upper_limit": 90,
            "lower_limit": -110,
            "period_1": 15,
            "period_2": 24,
            "stop": 1.5,
            "limit": 1.8
        },
        "EURCHF": {
            "upper_limit": 90,
            "lower_limit": -105,
            "period_1": 15,
            "period_2": 24,
            "stop": 2.8,
            "limit": 1.8
        },
        "GBPUSD": {
            "upper_limit": 90,
            "lower_limit": -100,
            "period_1": 18,
            "period_2": 18,
            "stop": 2.5,
            "limit": 2.1
        },
        "AUDUSD": {
            "upper_limit": 90,
            "lower_limit": -95,
            "period_1": 15,
            "period_2": 15,
            "stop": 2.0,
            "limit": 1.0
        },
        "EURJPY": {
            "upper_limit": 90,
            "lower_limit": -110,
            "period_1": 15,
            "period_2": 15,
            "stop": 2.5,
            "limit": 2.5
        },
        "AUDJPY": {
            "upper_limit": 90,
            "lower_limit": -110,
            "period_1": 21,
            "period_2": 15,
            "stop": 1.5,
            "limit": 1.5
        },
        "CHFJPY": {
            "upper_limit": 90,
            "lower_limit": -110,
            "period_1": 15,
            "period_2": 15,
            "stop": 2.0,
            "limit": 1.0
        },
        "EURAUD": {
            "upper_limit": 90,
            "lower_limit": -110,
            "period_1": 15,
            "period_2": 15,
            "stop": 2.0,
            "limit": 1.0
        },
        "EURSGD": {
            "upper_limit": 90,
            "lower_limit": -110,
            "period_1": 15,
            "period_2": 18,
            "stop": 1.8,
            "limit": 1.8
        },
        "GBPJPY": {
            "upper_limit": 90,
            "lower_limit": -105,
            "period_1": 21,
            "period_2": 24,
            "stop": 2.5,
            "limit": 1.8
        }
    }

    def __init__(self, config=None):
        super().__init__(config)
        if config is None:
            config = {}
        self.upper_limit = config.get("upper_limit", self.upper_limit)
        self.lower_limit = config.get("lower_limit", self.lower_limit)
        self.period_1 = config.get("period_1", self.period_1)
        self.period_2 = config.get("period_2", self.period_2)
        self.limit = config.get("limit", self.limit)
        self.stop = config.get("stop", self.stop)

    def predict(self, df: DataFrame) -> str:
        p1 = self.period_1 * -1
        p2 = self.period_1 * -1 + p1

        if len(df) > p2:
            last_rsi = df.tail(1).CCI_7.values[0]
            last_ema10 = df.tail(1).EMA_10.values[0]
            last_ema30 = df.tail(1).EMA_30.values[0]

            if last_rsi < self.lower_limit and \
                    last_ema10 > last_ema30 and \
                    len(df[-2:].loc[df.close < df.EMA_30]) > 0 and \
                    len(df[p1:-1].loc[df.EMA_10 > df.EMA_30]) == self.period_1 and \
                    len(df[p2:p1].loc[df.EMA_10 < df.EMA_30]) > 0:
                return self.BUY

            if last_rsi > self.upper_limit and \
                    last_ema30 > last_ema10 and \
                    len(df[self.period_1 * -1:].loc[df.close > df.EMA_30]) > 0 and \
                    len(df[self.period_2 * -1:-1].loc[df.EMA_10 > df.EMA_30]) > 0:
                return self.SELL


        return self.NONE

    def get_config(self) -> str:
        stop, limit = self.get_stop_limit()
        return f"Stop *: {self.stop} " \
               f"Limit *: {self.limit} " \
               f"Stop: {stop:5.4} " \
               f"Limit: {limit:5.4} " \
               f"U-Limit: {self.upper_limit} " \
               f"L-Limit: {self.lower_limit} " \
               f"P1: {self.period_1} " \
               f"P2: {self.period_2}"

    def get_settings(self,ticker:str):
        return self._settings.get(ticker,self._settings["default"])


    def set_config(self,ticker:str):
        settings = self.get_settings(ticker)

        self.stop = settings["stop"]
        self.limit = settings["limit"]
        self.period_1 = settings["period_1"]
        self.period_2 = settings["period_2"]
        self.upper_limit = settings["upper_limit"]
        self.lower_limit = settings["lower_limit"]
