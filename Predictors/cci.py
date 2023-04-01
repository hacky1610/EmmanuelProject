from finta import TA
from matplotlib import pyplot as plt
from Predictors.base_predictor import BasePredictor
from pandas import DataFrame

class CCI(BasePredictor):

    upper_limit = 100
    lower_limit = -100

    def __init__(self, config: dict):
        super().__init__(config)
        self.upper_limit = config.get("upper_limit", self.upper_limit)
        self.lower_limit = config.get("lower_limit", self.lower_limit)


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
        last_rsi = df.tail(1).CCI.values[0]
        if last_rsi > self.upper_limit:
            return self.SELL

        if last_rsi < self.lower_limit:
            return self.BUY
