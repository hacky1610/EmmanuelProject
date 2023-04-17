from Connectors import IG
from BL.data_processor import DataProcessor
from Tracing.Tracer import Tracer
from datetime import date, timedelta
from BL.analytics import Analytics
from Predictors import BasePredictor
from Connectors.tiingo import TradeType


class Trader:

    def __init__(self, ig: IG, tiingo, tracer: Tracer, predictor: BasePredictor, dataprocessor: DataProcessor,
                 analytics: Analytics):
        self._ig = ig
        self._dataprocessor = dataprocessor
        self._tiingo = tiingo
        self._tracer = tracer
        self._predictor = predictor
        self._analytics = analytics

        # features
        self._consider_spread = True

    def get_stop_limit(self, df, scaling: int, stop_factor:float=2.5, limit_factor:float=2.5):
        stop = int(abs(df.close - df.close.shift(-1)).mean() * stop_factor * scaling)
        limit = int(abs(df.close - df.close.shift(-1)).mean() * limit_factor * scaling)
        return stop, limit

    def trade(self, symbol: str, epic: str, spread: float, scaling: int, spread_limit:float=6,trade_type:TradeType=TradeType.FX,size:float=1.0):
        if spread > spread_limit:
            self._tracer.write(f"Spread is greater that {spread_limit} for {symbol}")
            return False

        trade_df = self._tiingo.load_data_by_date(symbol,
                                                  (date.today() - timedelta(days=5)).strftime("%Y-%m-%d"),
                                                  None, self._dataprocessor,trade_type=trade_type)

        if len(trade_df) == 0:
            self._tracer.error(f"Could not load train data for {symbol}")
            return False

        self._predictor.set_config(symbol)
        signal = self._predictor.predict(trade_df)

        if signal == BasePredictor.NONE:
            return False

        stop, limit = self.get_stop_limit(trade_df, scaling,self._predictor.stop,self._predictor.limit)

        openedPosition = self._ig.get_opened_positions_by_epic(epic)

        if signal == BasePredictor.BUY:
            if openedPosition is not None and openedPosition.direction == "BUY":
                self._tracer.write(f"There is already an opened position of {symbol} with direction {openedPosition.direction }")
                return False
            res = self._ig.buy(epic, stop, limit,size)
            self._tracer.write(f"Buy {symbol} with settings {self._predictor.get_config()}")
            return True
        elif signal == BasePredictor.SELL:
            if openedPosition is not None and openedPosition.direction == "SELL":
                self._tracer.write(
                    f"There is already an opened position of {symbol} with direction {openedPosition.direction}")
                return False
            res = self._ig.sell(epic, stop, limit,size)
            self._tracer.write(f"Sell {symbol} with settings {self._predictor.get_config()}")
            return True

        return False
