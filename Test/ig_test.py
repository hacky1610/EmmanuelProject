import unittest
from unittest.mock import MagicMock
from Connectors.IG import IG
from pandas import DataFrame,Series

from Connectors.market_store import Market
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

    def test_intelligent_stop_adapt_stop_level_called_Buy(self):
        ms = MagicMock()
        market = Market(ticker="EURUSD", pip_euro=1)
        ms.get_market = MagicMock(return_value=market)
        pos = Series(data=[10, 21, 21, 5 , 30, "BUY", "abcd", 1, "EURUSD"], index=["level","bid","offer","stopLevel","limitLevel","direction","dealId","scalingFactor","instrumentName"])
        self.ig.adapt_stop_level = MagicMock()
        self.ig.intelligent_stop_level(pos, ms )

        self.ig.adapt_stop_level.assert_called()

    def test_intelligent_stop_price_to_low_Buy(self):
        ms = MagicMock()
        market = Market(ticker="EURUSD", pip_euro=1)
        ms.get_market = MagicMock(return_value=market)
        pos = Series(data=[10, 11, 11, 5, 30, "BUY", "abcd", 1, "EURUSD"],
                     index=["level", "bid", "offer", "stopLevel", "limitLevel", "direction", "dealId", "scalingFactor",
                            "instrumentName"])
        self.ig.adapt_stop_level = MagicMock()
        self.ig.intelligent_stop_level(pos, ms)

        self.ig.adapt_stop_level.assert_not_called()

    def test_intelligent_stop_stop_level_already_changed_Buy(self):
        ms = MagicMock()
        market = Market(ticker="EURUSD", pip_euro=1)
        ms.get_market = MagicMock(return_value=market)
        pos = Series(data=[10, 21, 21, 18, 30, "BUY", "abcd", 1, "EURUSD"],
                     index=["level", "bid", "offer", "stopLevel", "limitLevel", "direction", "dealId", "scalingFactor",
                            "instrumentName"])
        self.ig.adapt_stop_level = MagicMock()
        self.ig.intelligent_stop_level(pos, ms)

        self.ig.adapt_stop_level.assert_not_called()

    def test_intelligent_stop_adapt_stop_level_called_Sell(self):
        ms = MagicMock()
        market = Market(ticker="EURUSD", pip_euro=1)
        ms.get_market = MagicMock(return_value=market)
        pos = Series(data=[30, 5, 5, 60 , 0, "SELL", "abcd", 1, "EURUSD"], index=["level","bid","offer","stopLevel","limitLevel","direction","dealId","scalingFactor","instrumentName"])
        self.ig.adapt_stop_level = MagicMock()
        self.ig.intelligent_stop_level(pos, ms )

        self.ig.adapt_stop_level.assert_called()

    def test_intelligent_stop_price_to_low_Sell(self):
        ms = MagicMock()
        market = Market(ticker="EURUSD", pip_euro=1)
        ms.get_market = MagicMock(return_value=market)
        pos = Series(data=[30, 29, 29, 60 , 0, "SELL", "abcd", 1, "EURUSD"],
                     index=["level", "bid", "offer", "stopLevel", "limitLevel", "direction", "dealId", "scalingFactor",
                            "instrumentName"])
        self.ig.adapt_stop_level = MagicMock()
        self.ig.intelligent_stop_level(pos, ms)

        self.ig.adapt_stop_level.assert_not_called()

    def test_intelligent_stop_stop_level_already_changed_Sell(self):
        ms = MagicMock()
        market = Market(ticker="EURUSD", pip_euro=1)
        ms.get_market = MagicMock(return_value=market)
        pos = Series(data=[30, 5, 5, 6 , 0, "SELL", "abcd", 1, "EURUSD"],
                     index=["level", "bid", "offer", "stopLevel", "limitLevel", "direction", "dealId", "scalingFactor",
                            "instrumentName"])
        self.ig.adapt_stop_level = MagicMock()
        self.ig.intelligent_stop_level(pos, ms)

        self.ig.adapt_stop_level.assert_not_called()



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
        cur = self.ig._get_currency("CS.D.USDCAD.MINI.IP")
        assert cur == "CAD"

        cur = self.ig._get_currency("CS.D.USDEUR.CFD.IP")
        assert cur == "EUR"


