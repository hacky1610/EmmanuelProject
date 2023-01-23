import unittest
from Envs.forexEnv import ForexEnv
from Connectors.Loader import Loader
from Envs.tradingEnv import Actions,Positions
import pathlib
import os
from Tracing.ConsoleTracer import ConsoleTracer
from Data.data_processor import DataProcessor

class StockEnvTest(unittest.TestCase):
    def setUp(self):
        currentDir = pathlib.Path(__file__).parent.resolve()
        csvPath = os.path.join(currentDir, "Data", "testData.csv")

        df = Loader.loadFromFile(csvPath,DataProcessor())
        self.envConfig = {
            "df": df,
            "window_size":2,
            "tracer":ConsoleTracer()
        }

    def test_tradingFirstBuy_shouldNotHaveAProfit(self):

        se = ForexEnv(self.envConfig )
        se.reset()
        obs, re, done, info = se.step(Actions.Buy.value)
        assert re == 0
        assert info["total_profit"] == 1.0

    def test_tradingSecondBuy_noReward(self):
        se = ForexEnv(self.envConfig )
        se.reset()
        se.step(Actions.Buy.value)
        obs, re, done, info = se.step(Actions.Sell.value)
        assert re == 0
        assert info["total_profit"] == 0.9995

    def test_tradingThirdBuy_aReward(self):
        se = ForexEnv(self.envConfig )
        se.reset()
        se.step(Actions.Buy.value)
        se.step(Actions.Buy.value)
        obs, re, done, info = se.step(Actions.Sell.value)
        assert re == 10
        assert info["total_profit"] == 1.09945

    def test_tradingThirdBuy_negativReward(self):
        c = self.envConfig.copy()
        se = ForexEnv(c)
        se.reset()
        se.step(Actions.Buy.value)
        se.step(Actions.Buy.value)
        se.step(Actions.Buy.value)
        obs, re, done, info = se.step(Actions.Sell.value)
        assert re == -10
        assert info["total_profit"] == 0.89955

    def test_doneFeature(self):
        se = ForexEnv(self.envConfig)
        se.reset()
        done = False
        loops = 0
        while not done:
            obs, re, done, info = se.step(Actions.Sell.value)
            loops += 1

        assert True == done
        assert 7 == loops

    def test_reporting(self):
        c = self.envConfig.copy()
        se = ForexEnv(c)
        se.reset()
        se.step(Actions.Buy.value)
        se.step(Actions.Buy.value)
        se.step(Actions.Buy.value)
        obs, re, done, info = se.step(Actions.Sell.value)
        report = se.get_report()
        assert len(report) > 0

    def test_rendering(self):
        c = self.envConfig.copy()
        se = ForexEnv(c)
        se.reset()
        se.step(Actions.Buy.value)
        se.step(Actions.Buy.value)
        se.step(Actions.Buy.value)
        obs, re, done, info = se.step(Actions.Sell.value)
        se.plot("./")


