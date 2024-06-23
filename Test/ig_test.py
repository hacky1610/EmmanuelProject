import unittest
from unittest.mock import MagicMock
from Connectors.IG import IG
from pandas import DataFrame,Series
import unittest
from unittest.mock import Mock, patch
from pandas import Series
from Connectors.market_store import MarketStore
from Connectors.deal_store import DealStore
from Connectors.predictore_store import PredictorStore
from Connectors.IG import IG
from Connectors.tiingo import TradeType


class IgTest(unittest.TestCase):

    def setUp(self):
        conf_reader = MagicMock()
        conf_reader.read_config = MagicMock(return_value={"ti_api_key":"key"})
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
        df = df.append(Series(["GBPUSD Mini","TRADEABLE","GBPUSD.de",100,102,10],index=["instrumentName","marketStatus","epic","offer","bid","scalingFactor"]),ignore_index=True)
        df = df.append(Series(["GBPUSD","NOTTRADEABLE","GBPUSD.de",100,102,10],index=["instrumentName","marketStatus","epic","offer","bid","scalingFactor"]),ignore_index=True)
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



    @patch('Connectors.IG.GenericPredictor')
    @patch('Connectors.IG.Indicators')
    def test_set_intelligent_stop_level_for_buy_direction(self, mock_indicators, mock_predictor):
        # Mocking objects
        position = Series({
            'level': 1.0,
            'bid': 1.1,
            'offer': 1.2,
            'stopLevel': 0.9,
            'limitLevel': 1.3,
            'direction': 'BUY',
            'dealId': '123',
            'scalingFactor': 1,
            'instrumentName': 'EUR/USD Mini'
        })
        market_store = Mock(spec=MarketStore)
        deal_store = Mock(spec=DealStore)
        predictor_store = Mock(spec=PredictorStore)
        ig = IG(None)

        # Mocking methods
        mock_predictor.get_open_limit_isl.return_value = False
        mock_predictor.get_isl_entry.return_value = 0.05
        market_store.get_market.return_value.get_euro_value.return_value = 0.1
        ig.get_stop_distance = Mock(return_value=0.05)

        # Call the method
        ig.set_intelligent_stop_level(position, market_store, deal_store, predictor_store)

        # Assertions
        ig._adjust_stop_level.assert_called_once_with('123', 1.3, 1.15, deal_store)

    @patch('Connectors.IG.GenericPredictor')
    @patch('Connectors.IG.Indicators')
    def test_set_intelligent_stop_level_for_sell_direction(self, mock_indicators, mock_predictor):
        # Mocking objects
        position = Series({
            'level': 1.0,
            'bid': 0.9,
            'offer': 0.8,
            'stopLevel': 1.1,
            'limitLevel': 0.7,
            'direction': 'SELL',
            'dealId': '123',
            'scalingFactor': 1,
            'instrumentName': 'EUR/USD Mini'
        })
        market_store = Mock(spec=MarketStore)
        deal_store = Mock(spec=DealStore)
        predictor_store = Mock(spec=PredictorStore)
        ig = IG(None)

        # Mocking methods
        mock_predictor.get_open_limit_isl.return_value = False
        mock_predictor.get_isl_entry.return_value = 0.05
        market_store.get_market.return_value.get_euro_value.return_value = 0.1
        ig.get_stop_distance = Mock(return_value=0.05)

        # Call the method
        ig.set_intelligent_stop_level(position, market_store, deal_store, predictor_store)

        # Assertions
        ig._adjust_stop_level.assert_called_once_with('123', 0.7, 0.85, deal_store)








