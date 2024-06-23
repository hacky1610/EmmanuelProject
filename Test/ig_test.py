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











