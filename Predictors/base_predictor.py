from pandas import DataFrame
from ray.tune import Trainable

class BasePredictor(Trainable):

    SELL = "sell"
    BUY = "buy"
    NONE = "none"
    limit = 0.0009
    stop = 0.0018
    METRIC = "reward"

    def __init__(self,config:dict):
        self.setup(config)

    def setup(self, config):
        self.limit = config.get("limit", self.limit)
        self.stop = config.get("stop", self.stop)
        self.df = config.get("df", self.stop)

    def predict(self,df:DataFrame) -> str:
        raise NotImplementedError

    def evaluate(self,df):
        reward = 0
        losses = 0
        wins = 0
        for i in range(len(df)):
            action = self.predict(df[:i+1])
            if action == self.NONE:
                continue

            open_price = df.close[i]
            if action == self.BUY:
                for j in range(i+1,len(df)):
                    high = df.high[j]
                    low = df.low[j]
                    if high > open_price + self.limit:
                        #Won
                        reward += high - open_price
                        wins += 1
                        break
                    elif low < open_price - self.stop:
                        #Loss
                        reward += low - open_price
                        losses += 1
                        break
            elif action == self.SELL:
                high = df.high[j]
                low = df.low[j]
                for j in range(i,len(df)):
                    if low < open_price - self.limit:
                        #Won
                        reward += open_price - low
                        wins += 1
                        break
                    elif high > open_price + self.stop:
                        reward += open_price - high
                        losses += 1
                        break


        return reward, wins / (wins + losses)

    def step(self):
        reward, success = self.evaluate(self.df)

        return {"done": True, self.METRIC: reward, "success": success }







