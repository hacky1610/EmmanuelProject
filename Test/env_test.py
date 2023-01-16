import unittest
from Envs.stocksEnv import StocksEnv
from Connectors.Loader import Loader
from Envs.tradingEnv import Actions,Positions
import pathlib
import os

class StockEnvTest(unittest.TestCase):
    def setUp(self):
        currentDir = pathlib.Path(__file__).parent.resolve()
        csvPath = os.path.join(currentDir, "Data", "testData.csv")

        self.df = Loader.loadFromFile(csvPath)

    def test_tradingFirstBuy_shouldNotHaveAProfit(self):

        se = StocksEnv(self.df,2,(2,6))
        se.reset()
        obs, re, done, info = se.step(Actions.Buy.value)
        assert re == 0
        assert info["total_profit"] == 1.0

    def test_tradingSecondBuy_noReward(self):
        se = StocksEnv(self.df, 2, (2, 6))
        se.reset()
        se.step(Actions.Buy.value)
        obs, re, done, info = se.step(Actions.Sell.value)
        assert 0 == re
        assert 0.98505 == info["total_profit"]

    def test_tradingThirdBuy_aReward(self):
        se = StocksEnv(self.df, 2, (2, 6))
        se.reset()
        se.step(Actions.Buy.value)
        se.step(Actions.Buy.value)
        obs, re, done, info = se.step(Actions.Sell.value)
        assert 10 == re
        assert 1.083555 == info["total_profit"]

    def test_tradingThirdBuy_negativReward(self):
        se = StocksEnv(self.df, 2, (2, 10))
        se.reset()
        se.step(Actions.Buy.value)
        se.step(Actions.Buy.value)
        se.step(Actions.Buy.value)
        obs, re, done, info = se.step(Actions.Sell.value)
        assert -10 == re
        assert 0.886545 == info["total_profit"]

