from Connectors.IG import IG
from Data.data_processor import DataProcessor
from Connectors.tiingo import Tiingo
from Tracing.Tracer import Tracer
from datetime import date, timedelta
from BL.analytics import Analytics
from Predictors import BasePredictor


class Trader:

    def __init__(self,ig: IG, tiingo: Tiingo, tracer: Tracer, predictor:BasePredictor, dataprocessor:DataProcessor, analytics:Analytics):
        self._ig = ig
        self._dataprocessor = dataprocessor
        self._tiingo = tiingo
        self._tracer = tracer
        self._predictor = predictor
        self._analytics = analytics

        #features
        self._consider_spread = True
        self._spread_limit = 6

    def trade(self,symbol):
        #if self._ig.has_opened_positions():
        #    return False

        trade_df = self._tiingo.load_data_by_date(symbol,
                                                  (date.today() - timedelta(days=5)).strftime("%Y-%m-%d"),
                                                  None, self._dataprocessor)
        if len(trade_df) == 0:
            self._tracer.error(f"Could not load train data for {symbol}")
            return False

        if self._ig.get_spread(symbol) > self._spread_limit:
            self._tracer.write(f"Spread is greater that {self._spread_limit} for {symbol}")
            return False

        signal = self._predictor.predict(trade_df)

        if signal == BasePredictor.NONE:
            return False

        if signal == BasePredictor.BUY:
            res = self._ig.buy(symbol)
            self._tracer.write(f"Buy {symbol}")
            return True
        elif signal == BasePredictor.SELL:
            res = self._ig.sell(symbol)
            self._tracer.write(f"Sell {symbol}")
            return True


        return False
