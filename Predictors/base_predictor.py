import os

from pandas import DataFrame

from BL.utils import get_project_dir
from Tracing.ConsoleTracer import ConsoleTracer


class BasePredictor:
    SELL = "sell"
    BUY = "buy"
    NONE = "none"
    limit = 2.0
    stop = 2.0
    METRIC = "reward"
    _tracer = ConsoleTracer()

    def __init__(self, config=None):
        if config is None:
            config = {}
        self.setup(config)

    def setup(self, config):
        self.limit = config.get("limit", self.limit)
        self.stop = config.get("stop", self.stop)
        self._tracer = config.get("tracer", ConsoleTracer())

    def predict(self, df: DataFrame) -> str:
        raise NotImplementedError

    def get_stop_limit(self,df):
        mean_diff = abs(df[-96:].close - df[-96:].close.shift(-1)).mean()
        return mean_diff * self.stop, mean_diff * self.limit

    def step(self,df_train:DataFrame, df_eval:DataFrame,analytics):
        reward, success, trade_freq, win_loss, avg_minutes = analytics.evaluate(self, df_train,df_eval)

        return {"done": True, self.METRIC: reward, "success": success, "trade_frequency": trade_freq,
                "win_loss": win_loss, "avg_minutes": avg_minutes}

    def _get_save_path(self,symbol:str) -> str:
        return os.path.join(get_project_dir(),"Settings",f"{symbol}.json")

    def load(self, symbol: str):
        raise NotImplementedError



