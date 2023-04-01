from pandas import DataFrame
from ray.tune import Trainable

class BasePredictor(Trainable):

    SELL = "sell"
    BUY = "buy"
    NONE = "none"
    limit = 0.0009
    stop = 0.0009
    METRIC = "reward"

    def __init__(self,config:dict):
        self.setup(config)

    def setup(self, config):
        self.limit = config.get("limit", self.limit)
        self.stop = config.get("stop", self.stop)
        self.df = config.get("df")
        self.df_eval = config.get("df_eval")

    def predict(self,df:DataFrame) -> str:
        raise NotImplementedError

    def evaluate(self,df_train,df_eval):
        reward = 0
        losses = 0
        wins = 0
        for i in range(len(df_train)):
            action = self.predict(df_train[:i+1])
            if action == self.NONE:
                continue

            open_price = df_train.close[i]
            future = df_eval[df_eval["date"] > df_train.date[i]]
            future.reset_index(inplace=True)
            if action == self.BUY:

                for j in range(len(future)):
                    close = future.close[j]

                    if close > open_price + self.limit:
                        #Won
                        reward += close - open_price
                        wins += 1
                        break
                    elif close < open_price - self.stop:
                        #Loss
                        reward += close - open_price
                        losses += 1
                        break
            elif action == self.SELL:
                for j in range(len(future)):
                    close = future.close[j]
                    if close < open_price - self.limit:
                        #Won
                        reward += open_price - close
                        wins += 1
                        break
                    elif close > open_price + self.stop:
                        reward += open_price - close
                        losses += 1
                        break


        return reward, wins / len(df_train)

    def step(self):
        reward, success = self.evaluate(self.df,self.df_eval)

        return {"done": True, self.METRIC: reward, "success": success }







