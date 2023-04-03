from finta import TA
from matplotlib import pyplot as plt
from Predictors import BasePredictor
from pandas import DataFrame

class RSI_STOCK_MACD(BasePredictor):

    upper_limit = 80
    lower_limit = 20

    def __init__(self, config: dict):
        super().__init__(config)
        self.upper_limit = config.get("upper_limit", self.upper_limit)
        self.lower_limit = config.get("lower_limit", self.lower_limit)
        self.limit = self.stop = 0.0029

    def predict(self,df:DataFrame) -> str:

        if (len(df) > 10):
            stoch_D_under  = len(df[-5:][df.STOCHD < self.lower_limit]) > 0
            stoch_K_under  = len(df[-5:][df.STOCHK < self.lower_limit]) > 0
            rsi_over = len(df[-1:][df.RSI > 50]) > 0

            if stoch_D_under and stoch_K_under  and rsi_over:

                return self.BUY

            stoch_D_over = len(df[-5:][df.STOCHD > self.lower_limit]) > 0
            stoch_K_over = len(df[-5:][df.STOCHK > self.lower_limit]) > 0
            rsi_under = len(df[-1:][df.RSI < 50]) > 0

            if stoch_D_over and stoch_K_over and rsi_under:
                return self.SELL



        return self.NONE


