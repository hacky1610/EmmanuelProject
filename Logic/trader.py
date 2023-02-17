from Connectors.IG import IG
from Data.data_processor import DataProcessor
from Logic.trainer import Trainer
from Connectors.tiingo import Tiingo
from Tracing.Tracer import Tracer
from datetime import date, timedelta


class Trader:

    def __init__(self, symbol: str, ig: IG, tiingo: Tiingo, tracer: Tracer):
        self._ig = ig
        self._dataprocessor = DataProcessor()
        self._symbol = symbol
        self._tiingo = tiingo
        self._tracer = tracer
        train_data = tiingo.load_data_by_date(symbol, "2022-08-15", "2022-12-31", self._dataprocessor, "1hour")
        if len(train_data) == 0:
            tracer.error("Could not load train data")
            assert False

        self._trainer = Trainer({"df": train_data})
        self._trainer.load_model("Models/Saturn.h5")

    def trade(self):
        trade_df = self._tiingo.load_data_by_date(self._symbol,
                                                  (date.today() - timedelta(days=20)).strftime("%Y-%m-%d"),
                                                  None, self._dataprocessor)
        if len(trade_df) == 0:
            self._tracer.error("Could not load train data")
            return

        trade_data = self._trainer.filter_dataframe(trade_df)
        val, signal = self._trainer.trade(trade_data.values[-16:])
        if not self._ig.has_opened_positions():
            if signal == "buy":
                res = self._ig.buy("CS.D.GBPUSD.CFD.IP")
                self._tracer.write(f"Buy -> expected {val}")
            else:
                res = self._ig.sell("CS.D.GBPUSD.CFD.IP")
                self._tracer.write(f"Sell -> expected {val}")

            if not res:
                self._tracer.error("Error while open trade")
