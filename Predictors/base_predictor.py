from pandas import DataFrame

class BasePredictor:

    SELL = "sell"
    BUY = "buy"
    NONE = "none"
    limit = 0.0009
    stop = 0.0018


    def __init__(self):
        pass

    def predict(self,df:DataFrame) -> str:
        raise NotImplementedError

    def evaluate(self,df):
        reward = 0
        for i in range(len(df)):
            action = self.predict(df[:i])
            if action == self.NONE:
                continue

            open_price = df.close[i]
            if action == self.BUY:
                for j in range(i,len(df)):
                    if df[j].high > open_price + self.limit:
                        #Won
                        reward += df[j].high - open_price
                    elif df[j].low < open_price - self.stop:
                        #Loss
                        reward += df[j].low - open_price
            elif action == self.SELL:
                for j in range(i,len(df)):
                    if df[j].low < open_price - self.limit:
                        #Won
                        reward += open_price - df[j].low
                    elif df[j].high > open_price + self.stop:
                        reward += open_price - df[j].high

        return reward






