from datetime import datetime
import os
import pandas as pd

from BL import get_project_dir, Analytics, DataProcessor
from Connectors import IG
from Connectors.dropbox_cache import DropBoxCache
from Connectors.tiingo import TradeType
from Tracing import Tracer
from Predictors.trainer import Trainer
from pandas import DataFrame
from Predictors.base_predictor import BasePredictor


class Trader:

    def __init__(self, ig: IG, tiingo, tracer: Tracer, predictor: BasePredictor, dataprocessor: DataProcessor,
                 analytics: Analytics, trainer: Trainer, cache: DropBoxCache):
        self._ig = ig
        self._dataprocessor = dataprocessor
        self._tiingo = tiingo
        self._tracer = tracer
        self._predictorClass = predictor
        self._analytics = analytics
        self._trainer = trainer
        self._min_win_loss = 0.7
        self._min_trades = 3
        self._cache = cache

    def get_stop_limit(self, df, scaling: int, stop_factor: float = 2.5, limit_factor: float = 2.5):
        stop = int(abs(df.close - df.close.shift(-1)).mean() * stop_factor * scaling)
        limit = int(abs(df.close - df.close.shift(-1)).mean() * limit_factor * scaling)
        return stop, limit

    @staticmethod
    def _get_spread(df: DataFrame, scaling: float) -> float:
        return (abs((df.close - df.close.shift(1))).median() * scaling) * 1.5

    @staticmethod
    def _get_evaluation():
        path = os.path.join(get_project_dir(), "Settings", "evaluation.json")
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
            predictor = self._predictorClass(tracer=self._tracer)
            predictor.load(symbol)
            self.trade(
                predictor=predictor,
                symbol=symbol,
                epic=market["epic"],
                spread=market["spread"],
                scaling=market["scaling"],
                trade_type=trade_type,
                size=market["size"],
                currency=market["currency"])

    def _report(self, df: DataFrame, symbol: str, reference: str):
        pass

    def _is_good(self, win_loss: float, trades: float, symbol: str):
        if win_loss < self._min_win_loss and trades >= self._min_trades:
            self._tracer.error(
                f"{symbol} Best result not good {win_loss} or  trades {trades} less than  {self._min_trades}")
            return False
        return True

    def trade(self, predictor: BasePredictor,
              symbol: str,
              epic: str,
              spread: float,
              scaling: int,
              trade_type: TradeType = TradeType.FX,
              size: float = 1.0,
              currency: str = "USD"):

        if (datetime.utcnow() - predictor.get_last_scan_time()).days >= 3:
            self._tracer.error(
                f"{symbol} Last evaluation to old")
            trade_df, df_eval = self._tiingo.load_train_data(symbol, self._dataprocessor, trade_type)
            _, _, _, win_loss, _, trades = self._analytics.evaluate(predictor,
                                                                    trade_df, df_eval,
                                                                    symbol)
            if not self._is_good(win_loss, trades, symbol):
                return False
        else:
            if not self._is_good(predictor.best_result, predictor.trades, symbol):
                return False
            trade_df = self._tiingo.load_trade_data(symbol, self._dataprocessor, trade_type)

        if len(trade_df) == 0:
            self._tracer.error(f"Could not load train data for {symbol}")
            return False

        spread_limit = self._get_spread(trade_df, scaling)
        if spread > spread_limit:
            self._tracer.debug(f"Spread {spread} is greater than {spread_limit} for {symbol}")
            return False

        signal = predictor.predict(trade_df)

        if signal == BasePredictor.NONE:
            return False

        stop, limit = self.get_stop_limit(trade_df, scaling, predictor.stop, predictor.limit)

        openedPosition = self._ig.get_opened_positions_by_epic(epic)

        if signal == BasePredictor.BUY:
            if openedPosition is not None and openedPosition.direction == "BUY":
                self._tracer.write(
                    f"There is already an opened position of {symbol} with direction {openedPosition.direction}")
                return False
            result, ref = self._ig.buy(epic, stop, limit, size, currency)
            if result:
                self._tracer.write(
                    f"Buy {symbol} with settings {predictor.get_config()}.")
                self._cache.save_report(trade_df, f"{symbol}_{ref}.csv")
                return True
        elif signal == BasePredictor.SELL:
            if openedPosition is not None and openedPosition.direction == "SELL":
                self._tracer.write(
                    f"There is already an opened position of {symbol} with direction {openedPosition.direction}")
                return False
            result, ref = self._ig.sell(epic, stop, limit, size, currency)
            if result:
                self._tracer.write(
                    f"Sell {symbol} with settings {predictor.get_config()} ")
                self._cache.save_report(trade_df, f"{symbol}_{ref}.csv")
                return True

        return False
