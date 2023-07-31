import os
from typing import List

import pandas as pd
from datetime import datetime
from BL import get_project_dir, Analytics, DataProcessor
from Connectors import IG
from Connectors.dropbox_cache import DropBoxCache
from Connectors.tiingo import TradeType
from Tracing import Tracer
from pandas import DataFrame
from Predictors.base_predictor import BasePredictor


class Trader:

    def __init__(self,
                 ig: IG,
                 tiingo,
                 tracer: Tracer,
                 predictor_class_list: List[type],
                 dataprocessor: DataProcessor,
                 analytics: Analytics,
                 cache: DropBoxCache):
        self._ig = ig
        self._dataprocessor = dataprocessor
        self._tiingo = tiingo
        self._tracer: Tracer = tracer
        self._predictor_class_list = predictor_class_list
        self._analytics = analytics
        self._min_win_loss = 0.65
        self._min_trades = 4
        self._cache = cache

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
            try:
                symbol = market["symbol"]
                self._tracer.set_prefix(symbol)
                for predictor_class in self._predictor_class_list:
                    self._tracer.debug(f"Try to trade {symbol} with {predictor_class.__name__}")
                    predictor = predictor_class(tracer=self._tracer, cache=self._cache)
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
            except Exception as EX:
                self._tracer.error(f"Error while trading {symbol} {EX}")

    def _report(self, df: DataFrame, symbol: str, reference: str):
        pass

    def _is_good(self, win_loss: float, trades: float, symbol: str):
        if win_loss >= 0.75 and trades >= 3:
            return True

        if win_loss >= self._min_win_loss and trades >= self._min_trades:
            return True

        self._tracer.error(
            f"{symbol} Best result not good {win_loss} or  trades {trades} less than  {self._min_trades}")
        return False

    @staticmethod
    def _evalutaion_up_to_date(last_scan_time):
        return (datetime.utcnow() - last_scan_time).days < 10

    def trade(self, predictor: BasePredictor,
              symbol: str,
              epic: str,
              spread: float,
              scaling: int,
              trade_type: TradeType = TradeType.FX,
              size: float = 1.0,
              currency: str = "USD"):

        if self._evalutaion_up_to_date(predictor.get_last_scan_time()):
            if not self._is_good(win_loss=predictor.get_last_result().get_win_loss(),
                                 trades=predictor.get_last_result().get_trades(),
                                 symbol=symbol):
                return False
            trade_df = self._tiingo.load_trade_data(symbol, self._dataprocessor, trade_type)
        else:
            self._tracer.error(f"{symbol} Last evaluation to old")
            return False

        if len(trade_df) == 0:
            self._tracer.error(f"Could not load train data for {symbol}")
            return False

        spread_limit = self._get_spread(trade_df, scaling)
        if spread > spread_limit:
            self._tracer.debug(f"Spread {spread} is greater than {spread_limit} for {symbol}")
            return False

        signal, stop, limit = predictor.predict(trade_df)
        scaled_stop = stop * scaling
        scaled_limit = limit * scaling

        if signal == BasePredictor.NONE:
            return False

        openedPosition = self._ig.get_opened_positions_by_epic(epic)

        if signal == BasePredictor.BUY:
            if openedPosition is not None and openedPosition.direction == "BUY":
                self._tracer.write(
                    f"There is already an opened position of {symbol} with direction {openedPosition.direction}")
                return False
            result, ref = self._ig.buy(epic, scaled_stop, scaled_limit, size, currency)
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
            result, ref = self._ig.sell(epic, scaled_stop, scaled_limit, size, currency)
            if result:
                self._tracer.write(
                    f"Sell {symbol} with settings {predictor.get_config()} ")
                self._cache.save_report(trade_df, f"{symbol}_{ref}.csv")
                return True

        return False
