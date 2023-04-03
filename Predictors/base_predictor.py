from pandas import DataFrame
from ray.tune import Trainable
import matplotlib.pyplot as plt
import pandas as pd

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

        plt.figure(figsize=(15, 6))
        plt.cla()
        chart, = plt.plot(pd.to_datetime(df_train["date"]), df_train["close"], color='#d3d3d3', alpha=0.5,
                          label="Chart")

        for i in range(len(df_train)):
            action = self.predict(df_train[:i+1])
            if action == self.NONE:
                continue

            open_price = df_train.close[i]
            future = df_eval[df_eval["date"] > df_train.date[i]]
            future.reset_index(inplace=True)
            if action == self.BUY:
                plt.plot(pd.to_datetime(df_train.date[i]), df_train.close[i], 'b^', label="Buy")
                for j in range(len(future)):
                    close = future.close[j]

                    if close > open_price + self.limit:
                        #Won
                        plt.plot(pd.to_datetime(future.date[j]), future.close[j], 'go')
                        reward += self.limit
                        wins += 1
                        break
                    elif close < open_price - self.stop:
                        #Loss
                        plt.plot(pd.to_datetime(future.date[j]), future.close[j], 'ro')
                        reward -=  self.stop
                        losses += 1
                        break
            elif action == self.SELL:
                for j in range(len(future)):
                    close = future.close[j]
                    if close < open_price - self.limit:
                        #Won
                        reward += self.limit
                        wins += 1
                        break
                    elif close > open_price + self.stop:
                        reward -= self.stop
                        losses += 1
                        break


        #plt.show()

        trades = wins + losses
        return reward, reward / trades, trades/ len(df_train) , wins / trades

    def step(self):
        reward, success , trade_freq, win_loss = self.evaluate(self.df,self.df_eval)

        return {"done": True, self.METRIC: reward, "success": success, "trade_frequency": trade_freq , "win_loss":win_loss}







