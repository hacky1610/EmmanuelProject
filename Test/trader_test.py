import copy
import unittest
from unittest.mock import MagicMock, call

from BL.datatypes import TradeAction
from BL.trader import Trader, TradeConfig, TradeResult
from BL.analytics import Analytics
from Connectors.tiingo import TradeType
from Tracing.ConsoleTracer import ConsoleTracer
from pandas import DataFrame, Series
from BL.data_processor import DataProcessor


class TraderTest(unittest.TestCase):

    def setUp(self):
        self._tracer = ConsoleTracer()
        self._dataProcessor = DataProcessor()
        self.analytics = Analytics(ConsoleTracer(), MagicMock())
        self._tiingo = MagicMock()
        self._mock_ig = MagicMock()
        self._mock_ig.buy = MagicMock(return_value=(True, {"date":"2016-03-04T00:00:00"}))
        self._mock_ig.sell = MagicMock(return_value=(True, {"date":"2016-03-04T00:00:00"}))
        self._trainer = MagicMock()
        self._predictor = MagicMock()
        self._predictor.stop = 2
        self._predictor.limit = 2
        self._predictor.best_result = 1.0
        self._predictor.trades = 100
        self._predictor_class_list = [MagicMock, MagicMock]

        self._stock_data = DataFrame()
        for i in range(20):
            self._stock_data = self._add_data(self._stock_data)

        self._tiingo.load_trade_data = MagicMock(return_value=self._stock_data)
        self._trader = Trader(ig=self._mock_ig,
                              tiingo=self._tiingo,
                              tracer=self._tracer,
                              dataprocessor=self._dataProcessor,
                              analytics=self.analytics,
                              predictor_class_list= self._predictor_class_list,
                              predictor_store=MagicMock(),
                              deal_storage=MagicMock(),
                              market_storage=MagicMock())
        self._trader._get_spread = MagicMock(return_value=1)
        self._trader._evalutaion_up_to_date = MagicMock(return_value=True)
        # Setzen der Test-Werte für _min_win_loss und _min_trades
        self._trader._min_win_loss = 0.7
        self._trader._min_trades = 5
        self._default_trade_config = TradeConfig(
            symbol="AAPL",
            epic="AAPL-12345",  # Annahme: Stellen Sie eine gültige Epic-Nummer ein.
            spread=0.5,
            scaling=10)

    @staticmethod
    def _add_data(df: DataFrame):
        return df.append(Series({
            "close": 23, "SMA7": 3, "EMA": 4, "BB_UPPER": 5, "BB_MIDDLE": 6, "BB_LOWER": 6, "ROC": 7, "%R": 8,
            "MACD": 4,
            "SIGNAL": 6}
        ), ignore_index=True)

    def test_trade_no_datafrom_tiingo(self):
        self._trader._is_good = MagicMock(return_value=True)
        self._tiingo.load_trade_data = MagicMock(return_value=DataFrame())
        self._predictor.predict = MagicMock(return_value=("none", 0, 0))
        res = self._trader.trade(predictor=self._predictor,
                                 config=self._default_trade_config)
        assert res == TradeResult.ERROR

    def test_trade_has_open_positions(self):
        positions = ["P1", "P2", "P3"]
        self._trader._execute_trade = MagicMock(return_value=(
            TradeResult.NOACTION,
            {"dealReference": "Ref",
             "dealId": "id",
             "date": "2016-03-04T00:00:00"}))
        self._mock_ig.get_opened_positions_by_epic = MagicMock(return_value=positions)
        self._predictor.predict = MagicMock(return_value=("buy", 1, 1))
        res = self._trader.trade(predictor=self._predictor,
                                 config=self._default_trade_config)
        self._mock_ig.buy.assert_not_called()
        assert res == TradeResult.NOACTION

        positions = ["P1", "P2"]
        self._trader._is_good = MagicMock(return_value=True)
        self._mock_ig.get_opened_positions_by_epic = MagicMock(return_value=positions)
        self._predictor.predict = MagicMock(return_value=("buy", 1, 1))
        res = self._trader.trade(predictor=self._predictor,
                                 config=self._default_trade_config)
        self._mock_ig.buy.asser_called()



    def test_trade_do_buy(self):
        self._predictor.predict = MagicMock(return_value=TradeAction.BUY)
        self._trader._get_spread = MagicMock(return_value=1)
        self._trader._execute_trade = MagicMock(return_value = (
            TradeResult.SUCCESS,
            {"dealReference":"Ref",
             "dealId":"id",
             "date":"2016-03-04T00:00:00"}))
        res = self._trader.trade(predictor=self._predictor,
                                 config=self._default_trade_config)
        self._mock_ig.buy.asser_called()
        assert res == TradeResult.SUCCESS

    def test_trade_do_sell(self):
        self._predictor.predict = MagicMock(return_value=TradeAction.SELL)
        self._trader._execute_trade = MagicMock(return_value=(
            TradeResult.SUCCESS,
            {"dealReference": "Ref",
             "dealId": "id",
             "date": "2016-03-04T00:00:00"}))
        res = self._trader.trade(predictor=self._predictor,
                                 config=self._default_trade_config)
        self._mock_ig.sell.asser_called()
        assert res == TradeResult.SUCCESS

    def test_trade_spread_to_big(self):
        self._trader._is_good = MagicMock(return_value=True)
        self._predictor.predict = MagicMock(return_value="buy")
        res = self._trader.trade(predictor=self._predictor,
                                 config=TradeConfig(
                                     symbol="AAPL",
                                     epic="AAPL-12345",  # Annahme: Stellen Sie eine gültige Epic-Nummer ein.
                                     spread=1.5,
                                     scaling=10)
                                 )
        self._mock_ig.buy.assert_not_called()
        self._mock_ig.sell.assert_not_called()
        assert res == TradeResult.ERROR

    def test_symbol_not_good(self):
        self._trader._execute_trade = MagicMock(return_value=(
            TradeResult.ERROR,
            {"dealReference": "Ref",
             "dealId": "id",
             "date": "2016-03-04T00:00:00"}))
        res = self._trader.trade(predictor=self._predictor,
                                 config=self._default_trade_config
                                 )
        self._mock_ig.buy.assert_not_called()
        self._mock_ig.sell.assert_not_called()
        assert res == TradeResult.ERROR

    def test_trade_no_data(self):
        self._trader._is_good = MagicMock(return_value=True)
        self._tiingo.load_trade_data = MagicMock(return_value=DataFrame())
        res = self._trader.trade(predictor=self._predictor,
                                 config=self._default_trade_config
                                 )
        self._mock_ig.buy.assert_not_called()
        self._mock_ig.sell.assert_not_called()
        assert res == TradeResult.ERROR

    def test_trade_action_none(self):
        self._trader._is_good = MagicMock(return_value=True)
        self._predictor.predict = MagicMock(return_value=TradeAction.NONE)
        self._trader._get_spread = MagicMock(return_value=1)
        res = self._trader.trade(predictor=self._predictor,
                                 config=self._default_trade_config
                                 )
        self._mock_ig.buy.assert_not_called()
        self._mock_ig.sell.assert_not_called()
        assert res == TradeResult.NOACTION






    def test_save_result(self):


        # Testaufruf der trade_markets-Funktion
        predictor = MagicMock()
        deal_response = {"A":1, "date":"2020-3-3"}
        self._trader._save_result(predictor,deal_response,"foo")


    def trade_bad_result(self):
        self._predictor.best_result = 0.1
        self._predictor.trades = 100
        self._predictor.predict = MagicMock(return_value=("none", 0, 0))
        res = self._trader.trade(predictor=self._predictor,
                                 config=self._default_trade_config
                                 )
        self._mock_ig.buy.assert_not_called()
        self._tiingo.load_trade_data.assert_not_called()

        self._predictor.best_result = 1.0
        self._predictor.trades = 2
        self._predictor.predict = MagicMock(return_value=("none", 0, 0))
        res = self._trader.trade(predictor=self._predictor,
                                 epic="myepic",
                                 symbol="mysymbol",
                                 spread=1.0,
                                 scaling=10)
        self._mock_ig.buy.assert_not_called()
        self._tiingo.load_trade_data.assert_not_called()
        assert res == False
