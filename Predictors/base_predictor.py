from pandas import DataFrame
from Predictors.evaluate import evaluate


class BasePredictor:
    SELL = "sell"
    BUY = "buy"
    NONE = "none"
    limit = 2.5
    stop = 2.5
    METRIC = "reward"

    def __init__(self, config=None):
        self.df_eval = None
        self.df = None
        if config is None:
            config = {}
        self.setup(config)

    def setup(self, config):
        self.limit = config.get("limit", self.limit)
        self.stop = config.get("stop", self.stop)
        self.df = config.get("df")
        self.df_eval = config.get("df_eval")

    def predict(self, df: DataFrame) -> str:
        raise NotImplementedError

    def get_stop_limit(self):
        mean_diff = abs(self.df[-30:].close - self.df[-30:].close.shift(-1)).mean()
        return mean_diff * self.stop, mean_diff * self.limit

    def step(self):
        reward, success, trade_freq, win_loss = evaluate(self, self.df, self.df_eval)

        return {"done": True, self.METRIC: reward, "success": success, "trade_frequency": trade_freq,
                "win_loss": win_loss}
