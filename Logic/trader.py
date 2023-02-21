from Connectors.IG import IG
from Data.data_processor import DataProcessor
from Logic.trainer import Trainer
from Connectors.tiingo import Tiingo
from Tracing.Tracer import Tracer
from datetime import date, timedelta
from Logic.analytics import Analytics


class Trader:

    def __init__(self, symbol: str, ig: IG, tiingo: Tiingo, tracer: Tracer, trainer:Trainer, dataprocessor:DataProcessor, analytics:Analytics):
        self._ig = ig
        self._dataprocessor = dataprocessor
        self._symbol = symbol
        self._tiingo = tiingo
        self._tracer = tracer
        self._trainer = trainer
        self._analytics = analytics

        #features
        self._consider_spread = True
        self._spread_limit = 6

    def trade(self):
        trade_df = self._tiingo.load_data_by_date(self._symbol,
                                                  (date.today() - timedelta(days=20)).strftime("%Y-%m-%d"),
                                                  None, self._dataprocessor)
        if len(trade_df) == 0:
            self._tracer.error("Could not load train data")
            return False

        if self._ig.has_opened_positions():
            return

        if self._ig.get_spread("CS.D.GBPUSD.CFD.IP") > self._spread_limit:
            self._tracer.write(f"Spread is greater that {self._spread_limit}")
            return

        if self._analytics.has_peak(trade_df):
            self._tracer.write(f"Dont trade because there is a peak")
            return

        trade_data = self._trainer.filter_dataframe(trade_df)
        val, signal = self._trainer.trade(trade_data.values[-16:])

        if signal == "buy":
            res = self._ig.buy("CS.D.GBPUSD.CFD.IP")
            self._tracer.write(f"Buy")
        else:
            res = self._ig.sell("CS.D.GBPUSD.CFD.IP")
            self._tracer.write(f"Sell")

        if not res:
            self._tracer.error("Error while open trade")

        return True
