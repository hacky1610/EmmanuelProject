from unittest.mock import MagicMock, patch, Mock
import pandas as pd
from pandas import DataFrame
import unittest
from pandas import Series
from trading_ig.rest import ApiExceededException

from Connectors.IG import IG
from Connectors.tiingo import TradeType


class IgTest(unittest.TestCase):

    def setUp(self):
        conf_reader = MagicMock()
        conf_reader.read_config = MagicMock(return_value={"ti_api_key": "key"})
        self.ig = IG(conf_reader, connect=False)
        self.ig._adjust_stop_level = MagicMock()
        self.ig.connect = MagicMock()
        self.ig.ig_service = MagicMock()

        # Erstelle einen Mock für tiingo
        self.mock_tiingo = Mock()

        # Simulierter DataFrame mit einer Spalte "ATR" und einer Zeile
        mock_atr_df = pd.DataFrame({"ATR": [0.0025]})

        # Stelle sicher, dass der Mock diese Daten zurückgibt
        self.mock_tiingo.load_trade_data = Mock(return_value=mock_atr_df)

        # Mock Stores
        self.market_store = Mock()
        self.deal_store = Mock()
        self.predictor_store = Mock()

        # Mock Market
        self.market = {"scaling": 10000, "currency": "USD"}

        # Mock Deal
        mock_deal = Mock()
        mock_deal.predictor_scan_id = "test_scan"
        mock_deal.is_manual_stop = True
        mock_deal.manual_stop_level = 1.0950
        self.deal_store.get_deal_by_deal_id = Mock(return_value=mock_deal)

        # Mock Position
        self.position = Mock()
        self.position.level = 1.1000
        self.position.direction = "BUY"
        self.position.bid = 1.1020
        self.position.offer = 1.1025
        self.position.stopLevel = 1.0900
        self.position.limitLevel = 1.1100
        self.position.dealId = "D12345"
        self.position.instrumentName = "EUR/USD"

        # Deal
        self.deal = Mock()
        self.deal.ticker = "EURUSD"
        self.deal.is_manual_stop = True
        self.deal.manual_stop_level = 1.0950
        self.deal.reached_level = False
        self.deal.size = 1
        self.deal.dealId = "D12345"
        self.deal.epic = "CS.D.EURUSD.MINI.IP"
        self.deal.direction = "buy"

        # Mock Predictor
        mock_predictor = Mock()
        mock_predictor.use_isl = Mock(return_value=True)
        mock_predictor.get_open_limit_isl = Mock(return_value=False)
        self.predictor_store.load_by_id = Mock(return_value={})

    def test_profit_below_minus_70_triggers_scale_trade(self):
        self.ig._get_atr = Mock(return_value=0.0025)
        self.deal_store.get_open_deals_by_ticker = Mock(return_value=[{}])
        self.ig.get_min_stop_distance = Mock(return_value=20)  # example minimum
        self.ig._calculate_profit_percentage = Mock(return_value=(-75.0, 0))
        self.ig._execute_trade = Mock(return_value=("SUCCESS", {
            "dealReference": "ref1",
            "dealId": "id1",
            "date": "2024-01-01T12:00:00"
        }))
        self.ig.find_market_by_symbol = Mock(return_value=self.market)

        result = self.ig.set_intelligent_stop_level(
            self.position, self.deal, self.deal_store, 10000, self.mock_tiingo
        )

        self.assertEqual(result["status"], "pending")
        self.ig._execute_trade.assert_called_once()

    def test_profit_above_40_sets_reached_level(self):
        self.ig._get_atr = Mock(return_value=0.0001)
        self.ig.get_min_stop_distance = Mock(return_value=20)
        self.ig._calculate_profit_percentage = Mock(return_value=(45.0, 0))
        self.ig._calculate_new_stop = Mock(return_value=1.1970)

        result = self.ig.set_intelligent_stop_level(
            self.position, self.deal, self.deal_store, 10000, self.mock_tiingo
        )

        self.assertTrue(self.deal.reached_level)
        self.assertEqual(result["status"], "success")

    def test_profit_above_80_adjusts_limit(self):
        self.ig._get_atr = Mock(return_value=0.0025)
        self.ig.get_min_stop_distance = Mock(return_value=20)
        self.ig._calculate_profit_percentage = Mock(return_value=(85.0, 0))
        self.ig._calculate_trailing_limit = Mock(return_value=1.1150)
        self.ig._calculate_new_stop = Mock(return_value=1.0970)

        self.deal.reached_level = True
        result = self.ig.set_intelligent_stop_level(
            self.position, self.deal, self.deal_store, 10000, self.mock_tiingo
        )

        self.ig._calculate_trailing_limit.assert_called_once()
        self.assertEqual(result["status"], "success")

    def test_manual_stop_is_hit_and_trade_closed(self):
        self.ig._get_atr = Mock(return_value=0.0025)
        self.ig.get_min_stop_distance = Mock(return_value=20)
        self.ig._calculate_profit_percentage = Mock(return_value=(10.0, 0))
        self.ig._calculate_new_stop = Mock(return_value=1.0950)
        self.ig._close_trade = Mock()
        self.deal.reached_level = True
        self.position.bid = 1.0949  # below manual stop
        result = self.ig.set_intelligent_stop_level(
            self.position, self.deal, self.deal_store, 10000, self.mock_tiingo
        )

        self.ig._close_trade.assert_called_once()
        self.assertEqual(result["status"], "closed")

    def test_stop_too_close_sets_manual_stop_instead(self):
        self.ig._get_atr = Mock(return_value=0.0025)
        self.ig.get_min_stop_distance = Mock(return_value=20)
        self.ig._calculate_profit_percentage = Mock(return_value=(50.0, 0))
        self.ig._calculate_new_stop = Mock(return_value=1.1015)  # very close to current price

        self.deal.reached_level = True
        self.deal.is_manual_stop = False

        result = self.ig.set_intelligent_stop_level(
            self.position, self.deal, self.deal_store, 10000, self.mock_tiingo
        )

        self.assertTrue(self.deal.is_manual_stop)
        self.assertEqual(result["status"], "success")

    def test_stop_and_limit_significantly_changed(self):
        self.ig._get_atr = Mock(return_value=0.0025)
        self.ig.get_min_stop_distance = Mock(return_value=20)
        self.ig._calculate_profit_percentage = Mock(return_value=(85.0, 0))
        self.ig._calculate_trailing_limit = Mock(return_value=1.1200)
        self.ig._calculate_new_stop = Mock(return_value=1.1005)

        self.position.limitLevel = 1.1100
        self.position.stopLevel = 1.0900
        self.deal.reached_level = True
        self.deal.is_manual_stop = False

        result = self.ig.set_intelligent_stop_level(
            self.position, self.deal, self.deal_store, 10000, self.mock_tiingo
        )

        self.ig._adjust_stop_level.assert_called_once()
        self.assertEqual(result["status"], "success")

    def test_get_markets_no_return(self):
        self.ig.ig_service.fetch_sub_nodes_by_node = MagicMock(return_value={
            "nodes": [],
            "markets": []
        })
        res = self.ig.get_markets(TradeType.FX)
        assert len(res) == 0

    def test_get_markets_some_returns(self):
        df = DataFrame()
        new_row = Series(["GBPUSD Mini", "TRADEABLE", "GBPUSD.de", 100, 102, 10],
                         index=["instrumentName", "marketStatus", "epic", "offer", "bid", "scalingFactor"])
        df = pd.concat([df, new_row.to_frame().T], ignore_index=True)
        new_row = Series(["GBPUSD", "NOTTRADEABLE", "GBPUSD.de", 100, 102, 10],
                         index=["instrumentName", "marketStatus", "epic", "offer", "bid", "scalingFactor"])
        df = pd.concat([df, new_row.to_frame().T], ignore_index=True)
        self.ig.ig_service.fetch_sub_nodes_by_node = MagicMock(return_value={
            "nodes": [],
            "markets": df
        })
        self.ig.ig_service.search_markets = MagicMock(return_value=df)
        res = self.ig.get_markets(TradeType.FX)
        assert res[0]["epic"] == "GBPUSD.de"
        assert len(res) == 1

    def test_get_currency(self):
        cur = self.ig.get_currency("CS.D.USDCAD.MINI.IP")
        assert cur == "CAD"

        cur = self.ig.get_currency("CS.D.USDEUR.CFD.IP")
        assert cur == "EUR"

        cur = self.ig.get_currency("CS.D.USDTRY.CFD.IP")
        assert cur == "TRL"


    @patch('Connectors.IG.IGService')
    def test_get_markets_by_id_valid_data(self, MockIGService):
        mock_service = MockIGService.return_value
        mock_service.fetch_sub_nodes_by_node.return_value = {
            "nodes": [],
            "markets": DataFrame([{"epic": "CS.D.BCHUSD.CFD.IP", "marketStatus": "TRADEABLE"}])
        }
        self.ig.ig_service = mock_service

        result = self.ig._get_markets_by_id(12345)
        self.assertFalse(result.empty)
        self.assertEqual(result.iloc[0]["epic"], "CS.D.BCHUSD.CFD.IP")

    @patch('Connectors.IG.IGService')
    def test_get_markets_by_id_api_exceeded(self, MockIGService):
        mock_service = MockIGService.return_value
        mock_service.fetch_sub_nodes_by_node.side_effect = ApiExceededException
        self.ig.ig_service = mock_service

        result = self.ig._get_markets_by_id(12345)
        self.assertTrue(result.empty)

    @patch('Connectors.IG.IGService')
    def test_get_markets_by_id_exception(self, MockIGService):
        mock_service = MockIGService.return_value
        mock_service.fetch_sub_nodes_by_node.side_effect = Exception("Test Exception")
        self.ig.ig_service = mock_service

        result = self.ig._get_markets_by_id(12345)
        self.assertTrue(result.empty)

    # def test_successful_buy_trade(self):
    #     """Test a successful BUY trade where stop level gets adjusted"""
    #     position = pd.Series({
    #         "level": 1.1000, "bid": 1.1025, "offer": 1.1030,
    #         "stopLevel": 1.0980, "limitLevel": 1.1040,
    #         "direction": "BUY", "dealId": "123", "instrumentName": "EUR/USD"
    #     })
    #
    #     result = self.ig.set_intelligent_stop_level(position, self.market_store, self.deal_store,
    #                                                       self.predictor_store, self.mock_tiingo)
    #
    #     self.assertEqual(result["status"], "success")
    #     self.assertIn("Stop level adjusted", result["message"])
    #
    # def test_successful_sell_trade(self):
    #     """Test a successful SELL trade where stop level gets adjusted"""
    #     position = pd.Series({
    #         "level": 1.2000, "bid": 1.1980, "offer": 1.1975,
    #         "stopLevel": 1.2020, "limitLevel": 1.1960,
    #         "direction": "SELL", "dealId": "124", "instrumentName": "EUR/USD"
    #     })
    #
    #     result = self.ig.set_intelligent_stop_level(position, self.market_store, self.deal_store,
    #                                                       self.predictor_store, self.mock_tiingo)
    #
    #     self.assertEqual(result["status"], "success")
    #     self.assertIn("Stop level adjusted", result["message"])
    #
    # def test_no_change_due_to_small_gain(self):
    #     """Test case where profit is not large enough to adjust stop level"""
    #     position = pd.Series({
    #         "level": 1.1000, "bid": 1.1005, "offer": 1.1010,
    #         "stopLevel": 1.0980, "limitLevel": 1.1040,
    #         "direction": "BUY", "dealId": "125", "instrumentName": "EUR/USD"
    #     })
    #
    #     result = self.ig.set_intelligent_stop_level(position, self.market_store, self.deal_store,
    #                                                       self.predictor_store, self.mock_tiingo)
    #
    #     self.assertEqual(result["status"], "no_change")
    #
    # def test_error_on_missing_prices(self):
    #     """Test case where bid or offer price is missing"""
    #     position = pd.Series({
    #         "level": 1.1000, "bid": None, "offer": None,
    #         "stopLevel": 1.0980, "limitLevel": 1.1040,
    #         "direction": "BUY", "dealId": "126", "instrumentName": "EUR/USD"
    #     })
    #
    #     result = self.ig.set_intelligent_stop_level(position, self.market_store, self.deal_store,
    #                                                       self.predictor_store, self.mock_tiingo)
    #
    #     self.assertEqual(result["status"], "error")
    #     self.assertIn("Missing bid or offer price", result["message"])