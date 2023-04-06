from pandas import DataFrame
from Tracing.Tracer import Tracer

class Analytics:

    def __init__(self,tracer:Tracer):
        self._tracer = tracer
    def has_peak(self, df:DataFrame, lockback:int = 3, max_limit:float=2.5):
        mean_diff = (df["high"] - df["low"]).mean()

        max = (df[lockback * -1:]["high"] - df[lockback * -1:]["low"]).max()

        if max > mean_diff * max_limit:
            self._tracer.write(f"Peak of {max} compared to mean {mean_diff}. Limit times {max_limit} im the last {lockback} dates")
            return True

        return False

    def is_sleeping(self, df: DataFrame, lockback: int = 2, max_limit: float = 0.6):
        mean_diff = (df["high"] - df["low"]).mean()
        m = (df[lockback * -1:]["high"] - df[lockback * -1:]["low"]).mean()

        if m < mean_diff * max_limit:
            #
            self._tracer.write(f"No movement {m} in the last {lockback} dates")
            return True

        return False
