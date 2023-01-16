import unittest
from Agents.Renotte import Renotte
from unittest.mock import MagicMock
from Envs.stocksEnv import StocksEnv
import pandas as pd
from Connectors.Loader import Loader
from Envs.tradingEnv import Actions,Positions


class StockEnvTest(unittest.TestCase):

    def test_tradingFirstBuy_shouldNotHaveAProfit(self):
        df = Loader.loadFromFile("./Data/testData.csv")
        se = StocksEnv(df,2,(2,6))
        se.reset()
        obs, re, done, info = se.step(Actions.Buy.value)
        assert re == 0
        assert info["total_profit"] == 1.0

    def test_tradingSecondBuy_noReward(self):
        df = Loader.loadFromFile("./Data/testData.csv")
        se = StocksEnv(df, 2, (2, 6))
        se.reset()
        se.step(Actions.Buy.value)
        obs, re, done, info = se.step(Actions.Sell.value)
        assert 0 == re
        assert 0.98505 == info["total_profit"]

    def test_tradingThirdBuy_aReward(self):
        df = Loader.loadFromFile("./Data/testData.csv")
        se = StocksEnv(df, 2, (2, 6))
        se.reset()
        se.step(Actions.Buy.value)
        se.step(Actions.Buy.value)
        obs, re, done, info = se.step(Actions.Sell.value)
        assert 10 == re
        assert 1.083555 == info["total_profit"]

    def test_tradingThirdBuy_negativReward(self):
        df = Loader.loadFromFile("./Data/testData.csv")
        se = StocksEnv(df, 2, (2, 10))
        se.reset()
        se.step(Actions.Buy.value)
        se.step(Actions.Buy.value)
        se.step(Actions.Buy.value)
        obs, re, done, info = se.step(Actions.Sell.value)
        assert -10 == re
        assert 0.886545 == info["total_profit"]

