from pandas import DataFrame

from Predictors.base_predictor import BasePredictor


class RSI(BasePredictor):
    upper_limit = 66
    lower_limit = 33

    def __init__(self, config=None):
        super().__init__(config)
        if config is None:
            config = {}
        self.upper_limit = config.get("upper_limit", self.upper_limit)
        self.lower_limit = config.get("lower_limit", self.lower_limit)

    def predict(self, df: DataFrame) -> str:

        last_rsi = df.tail(1).RSI.values[0]
        if last_rsi < self.upper_limit:
            return self.SELL

        if last_rsi > self.lower_limit:
            return self.BUY
