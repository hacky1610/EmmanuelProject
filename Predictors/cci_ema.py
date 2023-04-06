from pandas import DataFrame

from Predictors import CCI


class CCI_EMA(CCI):
    upper_limit = 90
    lower_limit = -105
    period_1 = 24
    period_2 = 20

    def __init__(self, config=None):
        super().__init__(config)
        if config is None:
            config = {}
        self.upper_limit = config.get("upper_limit", self.upper_limit)
        self.lower_limit = config.get("lower_limit", self.lower_limit)
        self.period_1 = config.get("period_1", self.period_1)
        self.period_2 = config.get("period_2", self.period_2)
        self.limit = self.stop = 0.0029

    def predict(self, df: DataFrame) -> str:

        if len(df) > 10:
            last_rsi = df.tail(1).CCI_7.values[0]
            last_ema10 = df.tail(1).EMA_10.values[0]
            last_ema30 = df.tail(1).EMA_30.values[0]

            if last_rsi < self.lower_limit and \
                    last_ema10 > last_ema30 and \
                    len(df[self.period_1 * -1:].loc[df.close < df.EMA_30]) > 0 and \
                    len(df[self.period_2 * -1:-1].loc[df.EMA_10 < df.EMA_30]) > 0:
                return self.BUY

            if last_rsi > self.upper_limit and \
                    last_ema30 > last_ema10 and \
                    len(df[self.period_1 * -1:].loc[df.close > df.EMA_30]) > 0 and \
                    len(df[self.period_2 * -1:-1].loc[df.EMA_10 > df.EMA_30]) > 0:
                return self.SELL

        return self.NONE
