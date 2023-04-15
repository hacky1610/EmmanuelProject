from pandas import DataFrame
from Predictors.evaluate import evaluate


class BasePredictor:
    SELL = "sell"
    BUY = "buy"
    NONE = "none"
    limit = 3.0
    stop = 3.0
    METRIC = "reward"

    def __init__(self, config=None):
        if config is None:
            config = {}
        self.setup(config)

    def setup(self, config):
        self.limit = config.get("limit", self.limit)
        self.stop = config.get("stop", self.stop)

    def predict(self, df: DataFrame) -> str:
        raise NotImplementedError

    def get_stop_limit(self,df):
        mean_diff = abs(df[-96:].close - df[-96:].close.shift(-1)).mean()
        return mean_diff * self.stop, mean_diff * self.limit

    def step(self):
        reward, success, trade_freq, win_loss, avg_minutes = evaluate(self, self.df, self.df_eval)

        return {"done": True, self.METRIC: reward, "success": success, "trade_frequency": trade_freq,
                "win_loss": win_loss, "avg_minutes": avg_minutes}
