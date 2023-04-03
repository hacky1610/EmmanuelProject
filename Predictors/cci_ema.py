from finta import TA
from matplotlib import pyplot as plt
from Predictors import CCI
from pandas import DataFrame

class CCI_EMA(CCI):

    upper_limit = 90
    lower_limit = -105

    def __init__(self, config: dict):
        super().__init__(config)
        self.upper_limit = config.get("upper_limit", self.upper_limit)
        self.lower_limit = config.get("lower_limit", self.lower_limit)
        self.limit = self.stop = 0.0029


    def print(self,df):

        df = df.tail(77)
        plt.figure(figsize=(15, 6))
        plt.cla()
        plt.plot(df.close)
        plt.savefig("close.png")

        plt.figure(figsize=(15, 6))
        plt.cla()
        plt.plot(df.CCI)
        plt.savefig("cci.png")

    def predict(self,df:DataFrame) -> str:

        if (len(df) > 10):
            last_rsi = df.tail(1).CCI_7.values[0]
            last_ema10 = df.tail(1).EMA_10.values[0]
            last_ema30 = df.tail(1).EMA_30.values[0]

            foo = len(df[-5:][df.close < df.EMA_30])
            if last_rsi < self.lower_limit and last_ema10 > last_ema30 and foo > 0:
                return self.BUY

            foo = len(df[-5:][df.close > df.EMA_30])
            if last_rsi > self.upper_limit and last_ema30 > last_ema10 and foo > 0:
                return self.SELL


