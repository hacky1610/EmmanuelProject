from unittest.mock import MagicMock, patch
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
        self.ig = IG(conf_reader)

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