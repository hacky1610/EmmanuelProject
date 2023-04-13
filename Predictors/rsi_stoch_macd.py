from finta import TA
from matplotlib import pyplot as plt
from Predictors import BasePredictor
from pandas import DataFrame

class RSI_STOCK_MACD(BasePredictor):
    #https://www.youtube.com/watch?v=6c5exPYoz3U
    upper_limit = 80
    lower_limit = 20
    period_1 = 11
    period_2 = 11

    def __init__(self, config: dict):
        super().__init__(config)
        self.upper_limit = config.get("upper_limit", self.upper_limit)
        self.lower_limit = config.get("lower_limit", self.lower_limit)
        self.period_1 = config.get("period_1", self.period_1)
        self.period_2 = config.get("period_2", self.period_2)
        self.limit = config.get("limit", self.limit)
        self.stop = config.get("stop", self.stop)

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

    def predict(self,df:DataFrame) -> str:
        p1 = self.period_1 * -1
        p2 = self.period_2 * -1

        sd = df.tail(1).STOCHD.values[0]
        sk = df.tail(1).STOCHK.values[0]
        sig = df.tail(1).SIGNAL.values[0]
        mac = df.tail(1).MACD.values[0]
        rsi = df.tail(1).RSI.values[0]

        if (len(df) > max(abs(p1),abs(p2))):
            if rsi > 50 and mac > sig and sd < self.upper_limit and sk < self.upper_limit:
                stoch_D_oversold = len(df[p1:][df.STOCHD < self.lower_limit]) > 0
                stoch_K_oversold = len(df[p1:][df.STOCHK < self.lower_limit]) > 0
                MACD_UNDER_SIGNAL = len(df[p2:-1][df.MACD < df.SIGNAL]) > 0
                if stoch_D_oversold and stoch_K_oversold and MACD_UNDER_SIGNAL:
                    return self.BUY

            #Sell
            if rsi < 50 and mac < sig and sd > self.lower_limit and sk > self.lower_limit:
                stoch_D_overbought = len(df[p1:][df.STOCHD > self.upper_limit]) > 0
                stoch_K_overbought = len(df[p1:][df.STOCHK > self.upper_limit]) > 0
                MACD_OVER_SIGNAL = len(df[p2:-1][df.MACD > df.SIGNAL]) > 0
                if stoch_D_overbought and stoch_K_overbought and MACD_OVER_SIGNAL:
                    return self.SELL



        return self.NONE


