import os.path
import json
from Predictors.base_predictor import BasePredictor
from pandas import DataFrame, Series
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer


class EmaMacd(BasePredictor):

    # https://www.youtube.com/watch?v=6c5exPYoz3U
    rsi_upper_limit = 80
    rsi_lower_limit = 23
    period_1 = 2
    period_2 = 3
    min_macd_diff = 0.0005

    def __init__(self, config=None, tracer: Tracer = ConsoleTracer()):
        super().__init__(config, tracer)
        if config is None:
            config = {}
        self.setup(config)

    def setup(self, config: dict):
        self.rsi_upper_limit = config.get("rsi_upper_limit", self.rsi_upper_limit)
        self.rsi_lower_limit = config.get("rsi_lower_limit", self.rsi_lower_limit)
        self.period_1 = config.get("period_1", self.period_1)
        self.period_2 = config.get("period_2", self.period_2)
        self.min_macd_diff = config.get("min_macd_diff", self.min_macd_diff)
        super().setup(config)

    def get_config(self) -> Series:
        return Series(["RSI_BB",
                       self.stop,
                       self.limit,
                       self.rsi_upper_limit,
                       self.rsi_lower_limit,
                       self.period_1,
                       self.period_2,
                       self.min_macd_diff,
                       self.version,
                       self.best_result,
                       self.best_reward,
                       self.frequence
                       ],
                      index=["Type", "stop", "limit", "rsi_upper_limit",
                             "rsi_lower_limit", "period_1", "period_2", "min_macd_diff", "version","best_result","best_reward","frequence"])

    def save(self, symbol: str):
        self.get_config().to_json(self._get_save_path(self.__class__.__name__, symbol))

    def saved(self, symbol):
        return os.path.exists(self._get_save_path(self.__class__.__name__, symbol))

    def load(self, symbol: str):
        if self.saved(symbol):
            with open(self._get_save_path(self.__class__.__name__, symbol)) as json_file:
                data = json.load(json_file)
                self.setup(data)
        else:
            self._tracer.debug(f"No saved settings of {symbol}")
        return self

    def predict(self, df: DataFrame) -> str:
        if len(df) < 10:
            return BasePredictor.NONE

        adx = df[-1:].ADX.item()
        bbWith = df[-1:].BBWIDTH.item()
        rsi = df[-1:].RSI.item()
        macd = df[-1:].MACD.item()
        signal = df[-1:].SIGNAL.item()

        if abs(macd - signal) < self.min_macd_diff:
            return BasePredictor.NONE

        self.save_last_state(f"ADX {adx} BB {bbWith}")

        #if df[-1:].ADX.item() > 25:
        #    return BasePredictor.NONE

        #if df[-1:].BBWIDTH.item() > 0.5:
        #    return BasePredictor.NONE

        res_ema = self.predict_ema_3(df,3)
        res_macd = self.predict_macd(df,True)
        res_bb = self.predict_bb_1(df)

        if res_ema == BasePredictor.BUY and \
                res_macd == BasePredictor.BUY and \
                res_bb == BasePredictor.BUY and \
                rsi < 75:
            return BasePredictor.BUY

        if res_ema == BasePredictor.SELL and \
                res_macd == BasePredictor.SELL and \
                res_bb == BasePredictor.SELL and \
                rsi > 25:
            return BasePredictor.SELL


        return BasePredictor.NONE