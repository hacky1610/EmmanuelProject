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

        # Mock Deal
        mock_deal = Mock()
        mock_deal.predictor_scan_id = "test_scan"
        mock_deal.is_manual_stop = True
        mock_deal.manual_stop_level = 1.0950
        self.deal_store.get_deal_by_deal_id = Mock(return_value=mock_deal)

        # Mock Predictor
        mock_predictor = Mock()
        mock_predictor.use_isl = Mock(return_value=True)
        mock_predictor.get_open_limit_isl = Mock(return_value=False)
        self.predictor_store.load_by_id = Mock(return_value={})

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