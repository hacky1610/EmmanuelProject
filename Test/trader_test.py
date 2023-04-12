import unittest
from unittest.mock import MagicMock
from BL.trader import Trader
from BL import Analytics
from Tracing.ConsoleTracer import ConsoleTracer
from pandas import DataFrame, Series
from BL.data_processor import DataProcessor


class TraderTest(unittest.TestCase):

    def setUp(self):
        self._tracer = ConsoleTracer()
        self._dataProcessor = DataProcessor()
        self._stock_data = DataFrame()
        self.analytics = Analytics(ConsoleTracer())
        for i in range(20):
            self._stock_data = self._add_data(self._stock_data)
        pass

    @staticmethod
    def _add_data(df: DataFrame):
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
        t = Trader(ig, tiingo, self._tracer, trainer, self._dataProcessor, self.analytics)
        res = t.trade("myepic", "mysymbol", 1.0, 2)
        assert res == False

    def test_trade_has_open_positions(self):
        tiingo = MagicMock()
        tiingo.load_data_by_date = MagicMock(return_value=self._stock_data)
        ig = MagicMock()
        ig.has_opened_positions = MagicMock(return_value=True)
        predictor = MagicMock()
        predictor.stop = 2.5
        predictor.limit = 2.5
        t = Trader(ig, tiingo, self._tracer, predictor, self._dataProcessor, self.analytics)
        res = t.trade("myepic", "mysymbol", 1.0, 2)
        ig.buy.assert_not_called()

    def test_trade_do_buy(self):
        tiingo = MagicMock()
        tiingo.load_data_by_date = MagicMock(return_value=self._stock_data)
        ig = MagicMock()
        ig.buy = MagicMock(return_value=True)
        ig.has_opened_positions = MagicMock(return_value=False)
        ig.get_spread = MagicMock(return_value=2)
        predictor = MagicMock()
        predictor.stop = 2.5
        predictor.limit = 2.5
        predictor.predict = MagicMock(return_value="buy")
        t = Trader(ig, tiingo, self._tracer, predictor, self._dataProcessor, self.analytics)
        res = t.trade("myepic", "mysymbol", 1.0, 2)
        ig.buy.assert_called()



    def test_trade_do_sell(self):
        tiingo = MagicMock()
        tiingo.load_data_by_date = MagicMock(return_value=self._stock_data)
        ig = MagicMock()
        ig.sell = MagicMock(return_value=True)
        ig.has_opened_positions = MagicMock(return_value=False)
        ig.get_spread = MagicMock(return_value=2)
        predictor = MagicMock()
        predictor.stop = 2.5
        predictor.limit = 2.5
        predictor.predict = MagicMock(return_value="sell")
        t = Trader(ig, tiingo, self._tracer, predictor, self._dataProcessor, self.analytics)
        res = t.trade("myepic", "mysymbol", 1.0, 2)
        ig.sell.assert_called()

    def test_trade_spread_to_big(self):
        tiingo = MagicMock()
        tiingo.load_data_by_date = MagicMock(return_value=self._stock_data)
        ig = MagicMock()
        predictor = MagicMock()
        predictor.stop = 2.5
        predictor.limit = 2.5
        predictor.predict = MagicMock(return_value="buy")
        t = Trader(ig, tiingo, self._tracer, predictor, self._dataProcessor, self.analytics)
        res = t.trade("myepic", "mysymbol", 10.0, 2)
        predictor.predict.assert_not_called()

    def test_trade_no_action(self):
        tiingo = MagicMock()
        tiingo.load_data_by_date = MagicMock(return_value=self._stock_data)
        ig = MagicMock()
        ig.buy = MagicMock(return_value=True)
        predictor = MagicMock()
        predictor.stop = 2.5
        predictor.limit = 2.5
        predictor.predict = MagicMock(return_value="none")
        t = Trader(ig, tiingo, self._tracer, predictor, self._dataProcessor, self.analytics)
        res = t.trade("myepic", "mysymbol", 4, 2)
        ig.buy.assert_not_called()
