import copy
import unittest
from datetime import datetime
from unittest.mock import MagicMock, call

import pandas as pd

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
        self._tracer.debug = MagicMock()
        self._tracer.warning = MagicMock()
        self._dataProcessor = DataProcessor()
        self.analytics = Analytics(ConsoleTracer(), MagicMock())
        self._tiingo = MagicMock()
        self._mock_ig = MagicMock()
        self._mock_ig.buy = MagicMock(return_value=(True, {"date":"2016-03-04T00:00:00"}))
        self._mock_ig.sell = MagicMock(return_value=(True, {"date":"2016-03-04T00:00:00"}))
        self._mock_ig.get_min_stop_distance = MagicMock(return_value=4)
        market  = MagicMock()
        market.get_pip_value = MagicMock(return_value=10)
        self._mock_market_store = MagicMock()
        self._mock_market_store.get_market = MagicMock(return_value=market)
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
        self._deal_storage = MagicMock()
        self._trader = Trader(ig=self._mock_ig,
                              tiingo=self._tiingo,
                              tracer=self._tracer,
                              dataprocessor=self._dataProcessor,
                              analytics=self.analytics,
                              predictor_class_list= self._predictor_class_list,
                              predictor_store=MagicMock(),
                              deal_storage=self._deal_storage,
                              market_storage=self._mock_market_store)
        self._trader._evalutaion_up_to_date = MagicMock(return_value=True)
        # Setzen der Test-Werte für _min_win_loss und _min_trades
        self._trader._min_win_loss = 0.7
        self._trader._min_trades = 5
        self._trader._calc_profit = MagicMock()
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

    def test_symbol_not_good(self):
        self._trader._execute_trade = MagicMock(return_value=(
            TradeResult.ERROR,
            {"dealReference": "Ref",
             "dealId": "id",
             "date": "2016-03-04T00:00:00"}))
        self._mock_ig.get_min_stop_distance = MagicMock(return_value=4)
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

    def test_check_ig_performance_false(self):
        self._trader._check_ig_performance = False
        result = self._trader._is_good_ticker("AAPL", min_avg_profit=10, min_deal_count=1)
        self.assertTrue(result, "Result should be True when _check_ig_performance is False.")

    def test_less_than_8_deals(self):
        deals = MagicMock()
        deals.__len__.return_value = 7
        self._trader._tracer.debug = MagicMock()
        self._trader._check_ig_performance = True
        self._trader._deal_storage.get_closed_deals_by_ticker_not_older_than_df.return_value = deals

        result = self._trader._is_good_ticker("AAPL",min_avg_profit=10, min_deal_count=7)
        self.assertFalse(result, "Result should be False when less than 8 deals are returned.")
        self._trader._tracer.debug.assert_called_with("To less deals")

    def test_more_than_7_deals_profit_greater_than_100(self):
        deals = MagicMock()
        deals.__len__.return_value = 8
        deals.profit.sum.return_value = 101
        self._trader._tracer.debug = MagicMock()
        self._trader._check_ig_performance = True
        self._trader._deal_storage.get_closed_deals_by_ticker_not_older_than_df.return_value = deals

        result = self._trader._is_good_ticker("AAPL",min_avg_profit=10, min_deal_count=7)
        self.assertTrue(result, "Result should be True when more than 7 deals and profit is greater than 100.")

    def test_more_than_7_deals_profit_less_than_100(self):
        deals = MagicMock()
        deals.__len__.return_value = 8
        deals.profit.sum.return_value = 40
        self._trader._deal_storage.get_closed_deals_by_ticker_not_older_than_df.return_value = deals
        self._trader._check_ig_performance = True
        self._trader._tracer.debug = MagicMock()

        result = self._trader._is_good_ticker("AAPL",min_avg_profit=10, min_deal_count=7)
        self.assertFalse(result, "Result should be False when more than 7 deals and profit is less than 50.")

    def test_empty_transaction_history(self):
        self._trader._deal_storage.get_deal_by_ig_id = MagicMock()
        self._trader._ig.get_transaction_history.return_value = pd.DataFrame()
        self._trader.update_deals()
        self._trader._deal_storage.get_deal_by_ig_id.assert_not_called()

    def test_no_deal_found(self):
        data = {
            'instrumentName': ['EUR/USD'],
            'openDateUtc': ['2023-08-05T00:00:00'],
            'profitAndLoss': ['€0'],
            'openLevel': ['1.1'],
            'closeLevel': ['1.2'],
            'dateUtc': ['2023-08-05T12:00:00']
        }
        hist = pd.DataFrame(data)
        self._trader._ig.get_transaction_history.return_value = hist
        self._trader._deal_storage.get_deal_by_ig_id.return_value = None

        self._trader.update_deals()
        self._trader._tracer.debug.assert_called_with("No deal for 2023-08-05T00:00:00 and EURUSD")

    def test_deal_found_and_updated(self):
        data = {
            'instrumentName': ['EUR/USD'],
            'openDateUtc': ['2023-08-05T00:00:00'],
            'profitAndLoss': ['€100'],
            'openLevel': ['1.1'],
            'closeLevel': ['1.2'],
            'dateUtc': ['2023-08-05T12:00:00']
        }
        hist = pd.DataFrame(data)
        self._trader._ig.get_transaction_history.return_value = hist

        deal_mock = MagicMock()
        self._trader._deal_storage.get_deal_by_ig_id.return_value = deal_mock

        self._trader.update_deals()

        deal_mock.profit = 100
        deal_mock.open_level = 1.1
        deal_mock.close_level = 1.2
        deal_mock.close_date_ig_datetime = datetime.strptime('2023-08-05T12:00:00', '%Y-%m-%dT%H:%M:%S')
        deal_mock.result = 1
        deal_mock.close.assert_called_once()
        self._deal_storage.save.assert_called_with(deal_mock)

    def test_deal_profit_zero(self):
        data = {
            'instrumentName': ['EUR/USD'],
            'openDateUtc': ['2023-08-05T00:00:00'],
            'profitAndLoss': ['€0'],
            'openLevel': ['1.1'],
            'closeLevel': ['1.2'],
            'dateUtc': ['2023-08-05T12:00:00']
        }
        hist = pd.DataFrame(data)
        self._trader._ig.get_transaction_history.return_value = hist

        deal_mock = MagicMock()
        self._trader._deal_storage.get_deal_by_ig_id.return_value = deal_mock

        market_details_mock = {'instrument': {'contractSize': '10'}}
        self._trader._ig.get_market_details.return_value = market_details_mock

        market_mock = MagicMock()
        self._trader._market_store.get_market.return_value = market_mock

        self._trader._calc_profit.return_value = 50

        self._trader.update_deals()

        self.assertEqual(deal_mock.profit, 50)
        self._trader._tracer.warning.assert_called_with(
            f"Problem with IG Calcululation. Profit is 0 Euro. Real profit is {deal_mock.profit} . Deal {deal_mock.dealId}"
        )

    def test_deal_profit_positive(self):
        data = {
            'instrumentName': ['EUR/USD'],
            'openDateUtc': ['2023-08-05T00:00:00'],
            'profitAndLoss': ['€100'],
            'openLevel': ['1.1'],
            'closeLevel': ['1.2'],
            'dateUtc': ['2023-08-05T12:00:00']
        }
        hist = pd.DataFrame(data)
        self._trader._ig.get_transaction_history.return_value = hist

        deal_mock = MagicMock()
        self._trader._deal_storage.get_deal_by_ig_id.return_value = deal_mock

        self._trader.update_deals()

        self.assertEqual(deal_mock.result, 1)

    def test_deal_profit_negative_or_zero(self):
        data = {
            'instrumentName': ['EUR/USD'],
            'openDateUtc': ['2023-08-05T00:00:00'],
            'profitAndLoss': ['€-100'],
            'openLevel': ['1.1'],
            'closeLevel': ['1.2'],
            'dateUtc': ['2023-08-05T12:00:00']
        }
        hist = pd.DataFrame(data)
        self._trader._ig.get_transaction_history.return_value = hist

        deal_mock = MagicMock()
        self._trader._deal_storage.get_deal_by_ig_id.return_value = deal_mock

        self._trader.update_deals()

        self.assertEqual(deal_mock.result, -1)






