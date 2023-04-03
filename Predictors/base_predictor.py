from pandas import DataFrame
from ray.tune import Trainable
from Predictors import evaluate

class BasePredictor(Trainable):

    SELL = "sell"
    BUY = "buy"
    NONE = "none"
    limit = 0.0029
    stop = 0.0029
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



    def step(self):
        reward, success , trade_freq, win_loss = evaluate(self,self.df,self.df_eval)

        return {"done": True, self.METRIC: reward, "success": success, "trade_frequency": trade_freq , "win_loss":win_loss}







