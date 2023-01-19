import unittest
from Envs.stocksEnv import StocksEnv
from Connectors.Loader import Loader
from Envs.tradingEnv import Actions,Positions
import pathlib
import os
from Tracing.ConsoleTracer import ConsoleTracer

class StockEnvTest(unittest.TestCase):
    def setUp(self):
        currentDir = pathlib.Path(__file__).parent.resolve()
        csvPath = os.path.join(currentDir, "Data", "testData.csv")

        df = Loader.loadFromFile(csvPath)
        self.envConfig = {
            "df": df,
            "window_size":2,
            "tracer":ConsoleTracer()
        }

    def test_tradingFirstBuy_shouldNotHaveAProfit(self):

        se = StocksEnv(self.envConfig )
        se.reset()
        obs, re, done, info = se.step(Actions.Buy.value)
        assert re == 0
        assert info["total_profit"] == 1.0

    def test_tradingSecondBuy_noReward(self):
        se = StocksEnv(self.envConfig )
        se.reset()
        se.step(Actions.Buy.value)
        obs, re, done, info = se.step(Actions.Sell.value)
        assert 0 == re
        assert 0.98505 == info["total_profit"]

    def test_tradingThirdBuy_aReward(self):
        se = StocksEnv(self.envConfig )
        se.reset()
        se.step(Actions.Buy.value)
        se.step(Actions.Buy.value)
        obs, re, done, info = se.step(Actions.Sell.value)
        assert 10 == re
        assert 1.083555 == info["total_profit"]

    def test_tradingThirdBuy_negativReward(self):
        c = self.envConfig.copy()
        se = StocksEnv(c)
        se.reset()
        se.step(Actions.Buy.value)
        se.step(Actions.Buy.value)
        se.step(Actions.Buy.value)
        obs, re, done, info = se.step(Actions.Sell.value)
        assert -10 == re
        assert 0.886545 == info["total_profit"]

    def test_doneFeature(self):
        se = StocksEnv(self.envConfig)
        se.reset()
        done = False
        loops = 0
        while not done:
            obs, re, done, info = se.step(Actions.Sell.value)
            loops += 1

        assert True == done
        assert 7 == loops


