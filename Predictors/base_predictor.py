import itertools
import json
import os
from pandas import DataFrame, Series

from BL.eval_result import EvalResult
from BL.utils import get_project_dir
from Connectors.dropbox_cache import BaseCache
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.Tracer import Tracer
import numpy as np
from datetime import datetime

class BasePredictor:
    SELL = "sell"
    BUY = "buy"
    NONE = "none"
    limit = 2.0
    stop = 2.0
    METRIC = "reward"
    version = "V1.0"
    model_version = ""
    last_scan = datetime(1970, 1, 1).isoformat()
    best_result = 0.0
    best_reward = 0.0
    frequence = 0.0
    trades = 0
    _tracer = ConsoleTracer()
    _last_scan: EvalResult = EvalResult()

    def __init__(self, config=None, cache: BaseCache = BaseCache(), tracer: Tracer = ConsoleTracer()):
        if config is None:
            config = {}
        self.setup(config)
        self._tracer = tracer
        self.lastState = ""
        self._cache = cache

    def setup(self, config):
        self._set_att(config, "limit")
        self._set_att(config, "stop")
        self._set_att(config, "version")
        self._last_scan = EvalResult(reward=config.get("_reward",0.0),
                                     trades=config.get("_trades",0),
                                     wins=config.get("_wins",0),
                                     len_df=config.get("_len_df",0),
                                     trade_minutes=config.get("_trade_minutes",0))

    def _set_att(self, config: dict, name: str):
        self.__setattr__(name, config.get(name, self.__getattribute__(name)))

    def predict(self, df: DataFrame) -> str:
        raise NotImplementedError

    def get_last_scan_time(self):
        return datetime.fromisoformat(self.last_scan)

    def get_stop_limit(self, df):
        mean_diff = abs(df[-96:].close - df[-96:].close.shift(-1)).mean()
        return mean_diff * self.stop, mean_diff * self.limit

    def get_mean_range(self, df):
        return abs(df.close - df.close.shift(-1)).mean()

    def step(self, df_train: DataFrame, df_eval: DataFrame, analytics) -> EvalResult:
        ev_result: EvalResult = analytics.evaluate(self, df_train, df_eval)
        self._last_scan = ev_result
        return ev_result

    def _get_save_path(self, predictor_name: str, symbol: str) -> str:
        return os.path.join(get_project_dir(), "Settings", f"{predictor_name}_{symbol}.json")

    def get_config(self):
        return Series([self.__class__,
                       self.stop,
                       self.limit,
                       self.version,
                       self.best_result,
                       self.best_reward,
                       self.trades,
                       self.frequence,
                       self.last_scan,
                       ],
                      index=["Type",
                             "stop",
                             "limit",
                             "version",
                             "best_result",
                             "best_reward",
                             "trades",
                             "frequence",
                             "last_scan",
                             ])

    def load(self, symbol: str):
        raise NotImplementedError

    def is_crossing(self, a, b):
        print((a - b).max() > 0 and (a - b).min() < 0)

    def get_trend(self, column, step=1):
        diff = column.diff(step)
        mean = (abs(diff)).mean()
        if diff[-1:].item() > mean:
            return 1
        elif diff[-1:].item() > mean * -1:
            return -1

        return 0

    def interpret_candle(self, candle):
        open = candle.open.item()
        close = candle.close.item()
        high = candle.high.item()
        low = candle.low.item()
        percentage = 0.4
        if close > open:
            # if (high - low) * percentage < close - open:
            return BasePredictor.BUY
        elif close < open:
            # if (high - low) * percentage < open - close:
            return BasePredictor.SELL

        return BasePredictor.NONE

    def check_macd_divergence(self, df):
        # Berechne den MACD-Indikator und das Signal
        # Extrahiere die MACD-Linie und das Signal

        macd_line = df.MACD.values
        signal_line = df.SIGNAL.values

        # Überprüfe, ob in den letzten 10 Zeiteinheiten eine Divergenz aufgetreten ist
        last_macd_line = macd_line[-10:]
        last_signal_line = signal_line[-10:]
        last_price = df['close'][-10:].values
        last_lowest_macd_line = np.argmin(last_macd_line)
        last_highest_macd_line = np.argmax(last_macd_line)
        last_lowest_price = np.argmin(last_price)
        last_highest_price = np.argmax(last_price)
        if last_lowest_macd_line < last_lowest_price:
            return 1
        elif last_highest_macd_line > last_highest_price:
            return -1
        else:
            return 0

    def check_rsi_divergence(self, df, step: int = 5):
        # Berechne den MACD-Indikator und das Signal
        # Extrahiere die MACD-Linie und das Signal

        rsi_line = df.RSI.values

        # Überprüfe, ob in den letzten 10 Zeiteinheiten eine Divergenz aufgetreten ist
        last_macd_line = rsi_line[step * -1:]
        last_price = df['close'][step * -1:].values
        last_lowest_macd_line = np.argmin(last_macd_line)
        last_highest_macd_line = np.argmax(last_macd_line)
        last_lowest_price = np.argmin(last_price)
        last_highest_price = np.argmax(last_price)
        if last_lowest_macd_line < last_lowest_price:
            return 1
        elif last_highest_macd_line > last_highest_price:
            return -1
        else:
            return 0

    def predict_ema_3(self, df, period: int = 2):
        period = df[period * -1:]

        ema_14_over_25 = len(period[period.EMA_14 > period.EMA_25]) == len(period)
        ema_25_over_50 = len(period[period.EMA_25 > period.EMA_50]) == len(period)

        ema_14_under_25 = len(period[period.EMA_14 < period.EMA_25]) == len(period)
        ema_25_under_50 = len(period[period.EMA_25 < period.EMA_50]) == len(period)

        if ema_14_over_25 and ema_25_over_50:
            return BasePredictor.BUY

        if ema_14_under_25 and ema_25_under_50:
            return BasePredictor.SELL

        return BasePredictor.NONE

    def calc_trend(self, df, period: int = 2):
        period = df[period * -1:]

        ema_14_over_25 = len(period[period.EMA_14 > period.EMA_25]) == len(period)
        ema_25_over_50 = len(period[period.EMA_25 > period.EMA_50]) == len(period)

        ema_14_under_25 = len(period[period.EMA_14 < period.EMA_25]) == len(period)
        ema_25_under_50 = len(period[period.EMA_25 < period.EMA_50]) == len(period)

        if ema_14_over_25 and ema_25_over_50:
            return 1

        if ema_14_under_25 and ema_25_under_50:
            return -1

        return 0

    def predict_macd(self, df, period: int = 2, consider_gradient: bool = False):
        current_macd_periode = df[period * -1:]
        macd_over_signal = len(current_macd_periode[current_macd_periode.MACD > current_macd_periode.SIGNAL]) == len(
            current_macd_periode)
        macd_under_signal = len(current_macd_periode[current_macd_periode.MACD < current_macd_periode.SIGNAL]) == len(
            current_macd_periode)

        cur_macd = df[-1:].MACD.item()
        cur_sig = df[-1:].SIGNAL.item()
        pre_macd = df[-2:-1].MACD.item()
        pre_sig = df[-2:-1].SIGNAL.item()

        if macd_over_signal:
            if consider_gradient:
                if cur_macd - cur_sig > pre_macd - pre_sig:
                    return BasePredictor.BUY
                else:
                    return BasePredictor.NONE

            return BasePredictor.BUY

        if macd_under_signal:
            if consider_gradient:
                if cur_sig - cur_macd > pre_sig - pre_macd:
                    return BasePredictor.SELL
                else:
                    return BasePredictor.NONE

            return BasePredictor.SELL

        return BasePredictor.NONE

    def predict_bb_1(self, df, period: int = 2):
        current_bb_periode = df[period * -1:]
        low_over = len(current_bb_periode[current_bb_periode.low > current_bb_periode.BB1_UPPER]) == len(
            current_bb_periode)
        high_under = len(current_bb_periode[current_bb_periode.high < current_bb_periode.BB_LOWER]) == len(
            current_bb_periode)

        if low_over:
            return BasePredictor.BUY

        if high_under:
            return BasePredictor.SELL

        return BasePredictor.NONE

    def save_last_state(self, text):
        self.lastState = text

    @staticmethod
    def _stop_limit_trainer(version: str):

        json_objs = []
        for stop, limit in itertools.product(
                [1.8, 2.0, 2.3, 2.7, 3.],
                [1.8, 2.0, 2.3, 2.7, 3.]):
            json_objs.append({
                "stop": stop,
                "limit": limit,
                "version": version
            })
        return json_objs

    @staticmethod
    def get_training_sets(version: str):
        return []

    def _get_filename(self,symbol):
        return f"{self.__class__.__name__}_{symbol}{self.model_version}.json"

    def set_result(self, result:EvalResult):
        self._last_scan = result

    def get_last_result(self) -> EvalResult:
        return self._last_scan

    def save(self, symbol: str):
        self.last_scan = datetime.utcnow().isoformat()
        data = self.get_config().append(self._last_scan.get_data())
        self._cache.save_settings(data.to_json(), self._get_filename(symbol))

    def load(self, symbol: str):
        json = self._cache.load_settings(self._get_filename(symbol))
        if json is not None:
            self.setup(json)

        return self
