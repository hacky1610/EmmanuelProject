from pandas import DataFrame, Series

from Predictors.cci import CCI


class CCI_PSAR(CCI):
    upper_limit = 60
    lower_limit = 35
    period_1 = 2
    period_2 = 4
    min_psar_jump = 0.002

    def __init__(self, config=None):
        super().__init__(config)
        if config is None:
            config = {}
        self.upper_limit = config.get("upper_limit", self.upper_limit)
        self.lower_limit = config.get("lower_limit", self.lower_limit)
        self.period_1 = config.get("period_1", self.period_1)
        self.period_2 = config.get("period_2", self.period_2)
        self.limit = config.get("limit", self.limit)
        self.stop = config.get("stop", self.stop)
        self.min_psar_jump = config.get("min_psar_jump", self.min_psar_jump)


    def predict(self, df: DataFrame) -> str:

        if len(df) > max(self.period_1, self.period_2):
            p1 = self.period_1 * -1
            p2 = self.period_2 * -1
            rsi_under = len(df[p1:][df.RSI < self.lower_limit]) > 0
            rsi_over = len(df[p1:][df.RSI > self.upper_limit]) > 0
            psar_jump = df.PSAR[p2:].pct_change().max() > self.min_psar_jump


            if rsi_under and psar_jump:
                return self.BUY

            if rsi_over and psar_jump:
                return self.SELL


        return self.NONE

    def get_config(self) :
        return Series(["RSI_Stoch",
                       self.stop,
                       self.limit,
                       self.upper_limit,
                       self.lower_limit,
                       self.period_1,
                       self.period_2,
                       self.min_psar_jump],
                      index=["Type", "Stop", "Limit", "Upper Limit", "Lower Limit",
                            "Period 1","Period 2", "PSAR"])

    def get_config_as_string(self) -> str:
        # stop, limit = self.get_stop_limit()
        return f"Stop *: {self.stop} " \
               f"Limit *: {self.limit} " \
               f"U-Limit: {self.upper_limit} " \
               f"L-Limit: {self.lower_limit} " \
               f"P1: {self.period_1} " \
               f"P2: {self.period_2} " \
               f"PSAR: {self.min_psar_jump} "

    def get_settings(self,ticker:str):
        return self._settings.get(ticker,self._settings["default"])


    def set_config(self,ticker:str):
        settings = self.get_settings(ticker)

        self.stop = settings["stop"]
        self.limit = settings["limit"]
        self.period_1 = settings["period_1"]
        self.period_2 = settings["period_2"]
        self.upper_limit = settings["upper_limit"]
        self.lower_limit = settings["lower_limit"]
