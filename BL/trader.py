import json
import os
import pandas as pd

from BL import get_project_dir
from Connectors import IG
from Connectors.tiingo import TradeType
from BL.analytics import Analytics
from BL.data_processor import DataProcessor
from Tracing import Tracer
from Predictors.trainer import Trainer
from pandas import DataFrame
from Predictors.base_predictor import BasePredictor


class Trader:

    def __init__(self, ig: IG, tiingo, tracer: Tracer, predictor: BasePredictor, dataprocessor: DataProcessor,
                 analytics: Analytics, trainer: Trainer):
        self._ig = ig
        self._dataprocessor = dataprocessor
        self._tiingo = tiingo
        self._tracer = tracer
        self._predictor = predictor
        self._analytics = analytics
        self._trainer = trainer
        self._min_win_loss = 0.7

    def get_stop_limit(self, df, scaling: int, stop_factor: float = 2.5, limit_factor: float = 2.5):
        stop = int(abs(df.close - df.close.shift(-1)).mean() * stop_factor * scaling)
        limit = int(abs(df.close - df.close.shift(-1)).mean() * limit_factor * scaling)
        return stop, limit

    @staticmethod
    def _get_spread(df: DataFrame, scaling: float) -> float:
        return (abs((df.close - df.close.shift(1))).median() * scaling) * 1.5

    @staticmethod
    def _get_evaluation():
        path = os.path.join(get_project_dir(),"Settings", "evaluation.json")
        if os.path.exists(path):
            return pd.read_json(path)
        return DataFrame()

    @staticmethod
    def _get_good_markets():
        results = Trader._get_evaluation()
        return results[results.win_loss > 0.7].symbol.values

    def trade_markets(self, trade_type: TradeType):
        currency_markets = self._ig.get_markets(trade_type)
        for market in currency_markets:
            symbol = market["symbol"]
            self._tracer.debug(f"Try to trade {symbol}")
            self.trade(
                symbol=symbol,
                epic=market["epic"],
                spread=market["spread"],
                scaling=market["scaling"],
                trade_type=trade_type,
                size=market["size"],
                currency=market["currency"])

    def trade(self, symbol: str, epic: str, spread: float, scaling: int, trade_type: TradeType = TradeType.FX,
              size: float = 1.0, currency: str = "USD"):

        self._predictor.load(symbol)

        if self._predictor.best_result < 0.67:
            self._tracer.error(f"{symbol} Best result not good {self._predictor.best_result}")
            return False

        trade_df = self._tiingo.load_live_data_last_days(symbol, self._dataprocessor, trade_type)

        if len(trade_df) == 0:
            self._tracer.error(f"Could not load train data for {symbol}")
            return False

        spread_limit = self._get_spread(trade_df, scaling)
        if spread > spread_limit:
            self._tracer.debug(f"Spread {spread} is greater than {spread_limit} for {symbol}")
            return False

        signal = self._predictor.predict(trade_df)

        if signal == BasePredictor.NONE:
            return False

        stop, limit = self.get_stop_limit(trade_df, scaling, self._predictor.stop, self._predictor.limit)

        openedPosition = self._ig.get_opened_positions_by_epic(epic)

        if signal == BasePredictor.BUY:
            if openedPosition is not None and openedPosition.direction == "BUY":
                self._tracer.write(
                    f"There is already an opened position of {symbol} with direction {openedPosition.direction}")
                return False
            if self._ig.buy(epic, stop, limit, size, currency):
                self._tracer.write(
                    f"Buy {symbol} with settings {self._predictor.get_config()}.")
                return True
        elif signal == BasePredictor.SELL:
            if openedPosition is not None and openedPosition.direction == "SELL":
                self._tracer.write(
                    f"There is already an opened position of {symbol} with direction {openedPosition.direction}")
                return False
            if self._ig.sell(epic, stop, limit, size, currency):
                self._tracer.write(
                    f"Sell {symbol} with settings {self._predictor.get_config()} ")
                return True

        return False



