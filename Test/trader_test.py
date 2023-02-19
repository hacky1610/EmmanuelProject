import unittest
from unittest.mock import MagicMock
from Logic.trader import Trader
from Tracing.ConsoleTracer import ConsoleTracer
from pandas import DataFrame,Series
from Data.data_processor import DataProcessor


class TraderTest(unittest.TestCase):

    def setUp(self):
        self._tracer = ConsoleTracer()
        self._dataProcessor = DataProcessor()
        self._stock_data = DataFrame()
        for i in range(20):
            self._stock_data = self._add_data(self._stock_data)
        pass

    def _add_data(self,df:DataFrame):
        return df.append(Series({
            "close": 23, "SMA7": 3, "EMA": 4, "BB_UPPER": 5, "BB_MIDDLE": 6, "BB_LOWER": 6, "ROC": 7, "%R": 8,
            "MACD": 4,
            "SIGNAL": 6}
        ), ignore_index=True)

    def test_trade_no_datafrom_tiingo(self):
        res = DataFrame()
        tiingo = MagicMock()
        tiingo.load_data_by_date = MagicMock(return_value=res)
        ig = MagicMock()
        trainer = MagicMock()
        t = Trader("USD",ig,tiingo,self._tracer,trainer,self._dataProcessor)
        res = t.trade()
        assert res == False

    def test_trade_has_open_positions(self):

        tiingo = MagicMock()
        tiingo.load_data_by_date = MagicMock(return_value=self._stock_data)
        ig = MagicMock()
        ig.has_opened_positions = MagicMock(return_value=True)
        trainer = MagicMock()
        t = Trader("USD", ig, tiingo, self._tracer, trainer, self._dataProcessor)
        res = t.trade()
        ig.buy.assert_not_called()

    def test_trade_do_buy(self):
        tiingo = MagicMock()
        tiingo.load_data_by_date = MagicMock(return_value=self._stock_data)
        ig = MagicMock()
        ig.buy = MagicMock(return_value=True)
        ig.has_opened_positions = MagicMock(return_value=False)
        ig.get_spread = MagicMock(return_value=2)
        trainer = MagicMock()
        trainer.trade = MagicMock(return_value=(None,"buy"))
        t = Trader("USD", ig, tiingo, self._tracer, trainer, self._dataProcessor)
        res = t.trade()
        ig.buy.assert_called()

