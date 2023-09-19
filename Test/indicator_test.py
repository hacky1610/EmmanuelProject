import unittest
import pandas as pd
from pandas import DataFrame

from BL.datatypes import TradeAction
from BL.indicators import Indicators  # Stellen Sie sicher, dass Sie den richtigen Modulnamen verwenden


class TestIndicators(unittest.TestCase):

    def setUp(self):
        # Erstellen Sie einige Testdaten als Pandas DataFrame
        data = {
            'close': [115]
        }

        self.df_small = pd.DataFrame(data)

        data = {
            'close': [100,100,100,115]
        }

        self.df_big = pd.DataFrame(data)
        self.indicators = Indicators()

    def test_ema_predict(self):

        # Teste Buy-Pfad
        data_buy = DataFrame()
        data_buy['EMA_10'] = [118]
        data_buy['EMA_20'] = [115]
        data_buy['EMA_30'] = [114]
        action_buy = self.indicators._ema_predict(data_buy)
        self.assertEqual(action_buy, TradeAction.BUY)

        # Teste Sell-Pfad
        data_sell = DataFrame()
        data_sell['EMA_10'] = [112]
        data_sell['EMA_20'] = [115]
        data_sell['EMA_30'] = [118]
        action_sell = self.indicators._ema_predict(data_sell)
        self.assertEqual(action_sell, TradeAction.SELL)

        # Teste None-Pfad
        data_none = DataFrame()
        data_none['EMA_10'] = [200]
        data_none['EMA_20'] = [115]
        data_none['EMA_30'] = [118]
        action_none = self.indicators._ema_predict(data_none)
        self.assertEqual(action_none, TradeAction.NONE)

    def test_rsi_predict(self):

        # Teste Buy-Pfad
        data_buy = DataFrame()
        data_buy['RSI'] = [51]
        action_buy = self.indicators._rsi_predict(data_buy)
        self.assertEqual(action_buy, TradeAction.BUY)

        # Teste Sell-Pfad
        data_sell = DataFrame()
        data_sell['RSI'] = [49]
        action_sell = self.indicators._rsi_predict(data_sell)
        self.assertEqual(action_sell, TradeAction.SELL)

        # Teste None-Pfad
        data_none = DataFrame()
        data_none['RSI'] = [50]
        action_none = self.indicators._rsi_predict(data_none)
        self.assertEqual(action_none, TradeAction.NONE)

    def test_rsi_30_70_predict(self):

        # Teste Buy-Pfad
        data_buy = DataFrame()
        data_buy['RSI_SMOOTH'] = [80]
        action_buy = self.indicators._rsi_smooth_30_70_predict(data_buy)
        self.assertEqual(action_buy, TradeAction.BUY)

        # Teste Sell-Pfad
        data_sell = DataFrame()
        data_sell['RSI_SMOOTH'] = [20]
        action_sell = self.indicators._rsi_smooth_30_70_predict(data_sell)
        self.assertEqual(action_sell, TradeAction.SELL)

        # Teste None-Pfad
        data_none = DataFrame()
        data_none['RSI_SMOOTH'] = [50]
        action_none = self.indicators._rsi_smooth_30_70_predict(data_none)
        self.assertEqual(action_none, TradeAction.NONE)

    def test_rsi_30_70_predict(self):

        # Teste Buy-Pfad
        data_buy = DataFrame()
        data_buy['RSI_SMOOTH'] = [80]
        action_buy = self.indicators._rsi_smooth_30_70_predict(data_buy)
        self.assertEqual(action_buy, TradeAction.BUY)

        # Teste Sell-Pfad
        data_sell = DataFrame()
        data_sell['RSI_SMOOTH'] = [20]
        action_sell = self.indicators._rsi_smooth_30_70_predict(data_sell)
        self.assertEqual(action_sell, TradeAction.SELL)

        # Teste None-Pfad
        data_none = DataFrame()
        data_none['RSI_SMOOTH'] = [50]
        action_none = self.indicators._rsi_smooth_30_70_predict(data_none)
        self.assertEqual(action_none, TradeAction.NONE)

    def test_rsi_slope_predict(self):

        # Teste Buy-Pfad
        data_buy = DataFrame()
        data_buy['RSI_SMOOTH'] = [80,80,60,80]
        action_buy = self.indicators._rsi_smooth_slope_predict(data_buy)
        self.assertEqual(action_buy, TradeAction.BUY)

        # Teste Sell-Pfad
        data_sell = DataFrame()
        data_sell['RSI_SMOOTH'] = [80, 80, 60, 50]
        action_sell = self.indicators._rsi_smooth_slope_predict(data_sell)
        self.assertEqual(action_sell, TradeAction.SELL)

    def test_macd_predict(self):

        # Teste Buy-Pfad
        data_buy = DataFrame()
        data_buy['MACD'] = [80]
        data_buy['SIGNAL'] = [70]
        action_buy = self.indicators._macd_predict(data_buy)
        self.assertEqual(action_buy, TradeAction.BUY)

        # Teste Sell-Pfad
        data_sell = DataFrame()
        data_sell['MACD'] = [80]
        data_sell['SIGNAL'] = [90]
        action_sell = self.indicators._macd_predict(data_sell)
        self.assertEqual(action_sell, TradeAction.SELL)

    def test_macd_cross_predict(self):

        # Teste Buy-Pfad
        data_buy = DataFrame()
        data_buy['MACD'] = [80,70,80,80]
        data_buy['SIGNAL'] = [70,80,70,70]
        action_buy = self.indicators._macd_crossing_predict(data_buy)
        self.assertEqual(action_buy, TradeAction.BUY)

        # Teste Sell-Pfad
        data_sell = DataFrame()
        data_sell['MACD'] = [80,80, 80, 70]
        data_sell['SIGNAL'] = [70, 70, 70, 80]
        action_sell = self.indicators._macd_crossing_predict(data_sell)
        self.assertEqual(action_sell, TradeAction.SELL)

    def test_candle(self):

        # Teste Buy-Pfad
        data_buy = DataFrame()
        data_buy['close'] = [80]
        data_buy['open'] = [60]
        data_buy['high'] = [66]
        data_buy['low'] = [66]
        action_buy = self.indicators._candle_predict(data_buy)
        self.assertEqual(action_buy, TradeAction.BUY)

        # Teste Sell-Pfad
        data_sell = DataFrame()
        data_sell['close'] = [60]
        data_sell['open'] = [80]
        data_sell['high'] = [66]
        data_sell['low'] = [80]
        action_sell = self.indicators._candle_predict(data_sell)
        self.assertEqual(action_sell, TradeAction.SELL)

    def test_macd_cross_predict(self):


        # Teste Buy-Pfad
        data_buy = DataFrame()
        data_buy['MACD'] = [80, 70, 80, 80]
        data_buy['SIGNAL'] = [70, 80, 70, 70]
        action_buy = self.indicators._macd_crossing_predict(data_buy)
        self.assertEqual(action_buy, TradeAction.BUY)

        # Teste Sell-Pfad
        data_sell = DataFrame()
        data_sell['MACD'] = [80, 80, 80, 70]
        data_sell['SIGNAL'] = [70, 70, 70, 80]
        action_sell = self.indicators._macd_crossing_predict(data_sell)
        self.assertEqual(action_sell, TradeAction.SELL)

    def test_ichimoku_chikou(self):


        # Teste Buy-Pfad
        data_buy = DataFrame()
        data_buy['CHIKOU'] = [80]
        data_buy['close'] = [70]
        action_buy = self.indicators._ichimoku_chikou_predict(data_buy)
        self.assertEqual(action_buy, TradeAction.BUY)

        # Teste Sell-Pfad
        data_sell = DataFrame()
        data_sell['CHIKOU'] = [80]
        data_sell['close'] = [90]
        action_sell = self.indicators._ichimoku_chikou_predict(data_sell)
        self.assertEqual(action_sell, TradeAction.SELL)

    def test_tenkan_kijun_chikou(self):


        # Teste Buy-Pfad
        data_buy = DataFrame()
        data_buy['TENKAN'] = [60,70,75,80]
        data_buy['KIJUN'] = [70,70,70,70]
        action_buy = self.indicators._ichimoku_tenkan_kijun_predict(data_buy)
        self.assertEqual(action_buy, TradeAction.BUY)

        # Teste Sell-Pfad
        data_sell = DataFrame()
        data_sell['TENKAN'] = [80, 70, 60, 55]
        data_sell['KIJUN'] = [70, 70, 70, 70]
        action_sell = self.indicators._ichimoku_tenkan_kijun_predict(data_sell)
        self.assertEqual(action_sell, TradeAction.SELL)

    def test_ichimoku_cloud(self):


        # Teste Buy-Pfad
        data_buy = DataFrame()
        data_buy['SENKOU_A'] = [80]
        data_buy['SENKOU_B'] = [70]
        data_buy['close'] = [90]
        action_buy = self.indicators._ichimoku_cloud_predict(data_buy)
        self.assertEqual(action_buy, TradeAction.BUY)

        # Teste Sell-Pfad
        data_sell = DataFrame()
        data_sell['SENKOU_A'] = [80]
        data_sell['SENKOU_B'] = [90]
        data_sell['close'] = [70]
        action_sell = self.indicators._ichimoku_cloud_predict(data_sell)
        self.assertEqual(action_sell, TradeAction.SELL)

        # Teste None-Pfad
        data_none = DataFrame()
        data_none['SENKOU_A'] = [80]
        data_none['SENKOU_B'] = [90]
        data_none['close'] = [100]
        action_none = self.indicators._ichimoku_cloud_predict(data_none)
        self.assertEqual(action_none, TradeAction.NONE)

    def test_adx(self):
        # Teste Both-Pfad
        data_both = DataFrame()
        data_both['ADX'] = [30]
        action_buy = self.indicators._adx_predict(data_both)
        self.assertEqual(action_buy, TradeAction.BOTH)

        # Teste Both-Pfad
        data_none = DataFrame()
        data_none['ADX'] = [10]
        action_none = self.indicators._adx_predict(data_none)
        self.assertEqual(action_none, TradeAction.NONE)
