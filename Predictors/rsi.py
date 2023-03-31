from finta import TA
from matplotlib import pyplot as plt
from Predictors.base_predictor import BasePredictor
from pandas import DataFrame

class RSI(BasePredictor):

    def print(self,df):

        df = df.tail(77)
        plt.figure(figsize=(15, 6))
        plt.cla()
        plt.plot(df.close)
        plt.savefig("close.png")

        plt.figure(figsize=(15, 6))
        plt.cla()
        plt.plot(df.RSI)
        plt.savefig("rsi.png")

    def predict(self,df:DataFrame) -> str:

        if df[-1].RSI > 70:
            return self.SELL

        if df[-1].RSI < 30:
            return self.BUY
