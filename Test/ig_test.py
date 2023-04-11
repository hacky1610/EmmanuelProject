import unittest
from unittest.mock import MagicMock
from Connectors.IG import IG
from pandas import DataFrame,Series


class IgTest(unittest.TestCase):

    def setUp(self):
        conf_reader = MagicMock()
        conf_reader.read_config = MagicMock(return_value={"ti_api_key":"key"})
        self.ig = IG(conf_reader)

    def test_get_markets_no_return(self):
        self.ig.ig_service.search_markets= MagicMock(return_value=[])
        res = self.ig.get_markets()
        assert len(res) == 0

    def test_get_markets_some_returns(self):
        df = DataFrame()
        df = df.append(Series(["GBPUSD Mini","TRADEABLE","GBPUSD.de",100,102,10],index=["instrumentName","marketStatus","epic","offer","bid","scalingFactor"]),ignore_index=True)
        df = df.append(Series(["GBPUSD","NOTTRADEABLE","GBPUSD.de",100,102,10],index=["instrumentName","marketStatus","epic","offer","bid","scalingFactor"]),ignore_index=True)
        self.ig.ig_service.search_markets = MagicMock(return_value=df)
        res = self.ig.get_markets()
        assert len(res) == 1

    def test_get_currency(self):
        cur = self.ig.get_currency("CS.D.USDCAD.MINI.IP")
        assert cur == "CAD"

        cur = self.ig.get_currency("CS.D.USDEUR.CFD.IP")
        assert cur == "EUR"


