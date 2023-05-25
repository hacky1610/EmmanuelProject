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
        self.analytics = Analytics(ConsoleTracer())
        self._tiingo = MagicMock()
        self._ig = MagicMock()
        self._ig.buy = MagicMock(return_value=(True,"1"))
        self._ig.sell = MagicMock(return_value=(True, "1"))
        self._trainer = MagicMock()
        self._predictor = MagicMock()
        self._predictor.stop = 2
        self._predictor.limit = 2
        self._predictor.best_result = 1.0
        self._predictor.trades = 100


        self._stock_data = DataFrame()
        for i in range(20):
            self._stock_data = self._add_data(self._stock_data)

        self._tiingo.load_trade_data = MagicMock(return_value=self._stock_data)
        self._trader = Trader(ig=self._ig,
                   tiingo=self._tiingo,
                   tracer=self._tracer,
                   dataprocessor=self._dataProcessor,
                   analytics=self.analytics,
                   trainer=self._trainer,
                   predictor=self._predictor,
                              cache=MagicMock())
        self._trader._get_spread = MagicMock(return_value=1)
        Trader._get_good_markets = MagicMock(return_value=["myepic"])


    @staticmethod
    def _add_data(df: DataFrame):
        return df.append(Series({
            "close": 23, "SMA7": 3, "EMA": 4, "BB_UPPER": 5, "BB_MIDDLE": 6, "BB_LOWER": 6, "ROC": 7, "%R": 8,
            "MACD": 4,
            "SIGNAL": 6}
        ), ignore_index=True)

    def test_trade_no_datafrom_tiingo(self):
        self._tiingo.load_data_by_date = MagicMock(return_value=DataFrame())

        res = self._trader.trade(predictor=self._predictor,
                                 epic="myepic",
                                 symbol="mysymbol",
                                 spread=1.0,
                                 scaling=10)
        assert res == False

    def test_trade_has_open_buy_positions(self):

        position = MagicMock()
        position.direction = "BUY"
        self._ig.get_opened_positions_by_epic = MagicMock(return_value=position)
        self._predictor.predict = MagicMock(return_value="buy")
        res = self._trader.trade(predictor=self._predictor,
                                 epic="myepic",
                                 symbol="mysymbol",
                                 spread=1.0,
                                 scaling=10)
        self._ig.buy.assert_not_called()
        self._ig.get_opened_positions_by_epic.assert_called()
        assert res == False

    def test_trade_has_open_sell_positions(self):
        position = MagicMock()
        position.direction = "SELL"
        self._ig.get_opened_positions_by_epic = MagicMock(return_value=position)
        self._predictor.predict = MagicMock(return_value="sell")
        res = self._trader.trade(predictor=self._predictor,
                                 epic="myepic",
                                 symbol="mysymbol",
                                 spread=1.0,
                                 scaling=10)
        self._ig.sell.assert_not_called()
        self._ig.get_opened_positions_by_epic.assert_called()
        assert res == False

    def test_trade_do_buy(self):
        self._predictor.predict = MagicMock(return_value="buy")
        self._trader._get_spread = MagicMock(return_value=1)
        res = self._trader.trade(predictor=self._predictor,
                                 epic="myepic",
                                 symbol="mysymbol",
                                 spread=1.0,
                                 scaling=10)
        self._ig.buy.asser_called()
        self._ig.get_opened_positions_by_epic.assert_called()
        assert res == True

    def test_trade_do_sell(self):
        self._predictor.predict = MagicMock(return_value="sell")
        res = self._trader.trade(predictor=self._predictor,
                                 epic="myepic",
                                 symbol="mysymbol",
                                 spread=1.0,
                                 scaling=10)
        self._ig.sell.asser_called()
        self._ig.get_opened_positions_by_epic.assert_called()
        assert res == True

    def test_trade_spread_to_big(self):
        self._predictor.predict = MagicMock(return_value="buy")
        res = self._trader.trade(predictor=self._predictor,
                                 epic="myepic",
                                 symbol="mysymbol",
                                 spread=100.0,
                                 scaling=10)
        self._ig.buy.assert_not_called()
        self._ig.sell.assert_not_called()
        assert res == False

    def test_symbol_not_good(self):
        res = self._trader.trade(predictor=self._predictor,
                                 epic="myepic",
                                 symbol="mysymbol",
                                 spread=1.0,
                                 scaling=10)
        self._ig.buy.assert_not_called()
        self._ig.sell.assert_not_called()
        assert res == False

    def test_trade_no_data(self):
        self._tiingo.load_trade_data = MagicMock(return_value=DataFrame())
        res = self._trader.trade(predictor=self._predictor,
                                 epic="myepic",
                                 symbol="mysymbol",
                                 spread=1.0,
                                 scaling=10)
        self._ig.buy.assert_not_called()
        self._ig.sell.assert_not_called()
        assert res == False

    def test_trade_action_none(self):
        self._predictor.predict = MagicMock(return_value="none")
        self._trader._get_spread = MagicMock(return_value=1)
        res = self._trader.trade(predictor=self._predictor,
                                 epic="myepic",
                                 symbol="mysymbol",
                                 spread=1.0,
                                 scaling=10)
        self._ig.buy.assert_not_called()
        self._ig.sell.assert_not_called()
        assert res == False

    def test_trade_bad_result(self):
        self._predictor.best_result = 0.1
        self._predictor.trades = 100
        res = self._trader.trade(predictor=self._predictor,
                                 epic="myepic",
                                 symbol="mysymbol",
                                 spread=1.0,
                                 scaling=10)
        self._ig.buy.assert_not_called()
        self._tiingo.load_trade_data.assert_not_called()

        self._predictor.best_result = 1.0
        self._predictor.trades = 2
        res = self._trader.trade(predictor=self._predictor,
                                 epic="myepic",
                                 symbol="mysymbol",
                                 spread=1.0,
                                 scaling=10)
        self._ig.buy.assert_not_called()
        self._tiingo.load_trade_data.assert_not_called()
        assert res == False

