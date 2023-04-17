from Connectors import IG
from BL.data_processor import DataProcessor
from Tracing.Tracer import Tracer
from BL.analytics import Analytics
from Predictors import BasePredictor
from Predictors.evaluate import evaluate
from Connectors.tiingo import TradeType
from pandas import DataFrame


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

    def get_stop_limit(self, df, scaling: int, stop_factor: float = 2.5, limit_factor: float = 2.5):
        stop = int(abs(df.close - df.close.shift(-1)).mean() * stop_factor * scaling)
        limit = int(abs(df.close - df.close.shift(-1)).mean() * limit_factor * scaling)
        return stop, limit

    def _get_spread(self, df: DataFrame, scaling: float) -> float:
        return (abs((df.close - df.close.shift(1))).median() * scaling) * 1.1

    def trade(self, symbol: str, epic: str, spread: float, scaling: int, trade_type: TradeType = TradeType.FX,
              size: float = 1.0):
        trade_df, df_eval =  self._tiingo.load_live_data(symbol,self._dataprocessor, trade_type)

        if len(trade_df) == 0:
            self._tracer.error(f"Could not load train data for {symbol}")
            return False

        spread_limit = self._get_spread(trade_df, scaling)
        if spread > spread_limit:
            self._tracer.debug(f"Spread {spread} is greater that {spread_limit} for {symbol}")
            return False

        self._predictor.set_config(symbol)

        reward, success, trade_freq, win_loss, avg_minutes = evaluate(self._predictor, trade_df, df_eval, False)

        if win_loss < 0.67:
            self._tracer.debug(f"Win Loss is to less {symbol} -> WL: {win_loss}")
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
            if self._ig.buy(epic, stop, limit, size):
                self._tracer.write(f"Buy {symbol} with settings {self._predictor.get_config()}. Testresult: WinLoss {win_loss}")
                return True
        elif signal == BasePredictor.SELL:
            if openedPosition is not None and openedPosition.direction == "SELL":
                self._tracer.write(
                    f"There is already an opened position of {symbol} with direction {openedPosition.direction}")
                return False
            if self._ig.sell(epic, stop, limit, size):
                self._tracer.write(f"Sell {symbol} with settings {self._predictor.get_config()} Testresult: WinLoss {win_loss}")
                return True

        return False
