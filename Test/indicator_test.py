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
            'close': [100, 100, 100, 115]
        }

        self.df_big = pd.DataFrame(data)
        self.indicators = Indicators()

    def test_ema_predict(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['EMA_10'] = [118]
        data['EMA_20'] = [115]
        data['EMA_30'] = [114]
        data = self.indicators._ema_predict(data)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Sell-Pfad
        data = DataFrame()
        data['EMA_10'] = [112]
        data['EMA_20'] = [115]
        data['EMA_30'] = [118]
        action = self.indicators._ema_predict(data)
        self.assertEqual(action, TradeAction.SELL)

        # Teste None-Pfad
        data = DataFrame()
        data['EMA_10'] = [200]
        data['EMA_20'] = [115]
        data['EMA_30'] = [118]
        action = self.indicators._ema_predict(data)
        self.assertEqual(action, TradeAction.NONE)

    def test_rsi_convergence_predict(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['high'] = [110, 110, 110, 110, 110, 80, 110, 110, 110, 110, 110, 70, 110]
        data['low'] = [90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90]
        data['RSI'] = [50, 50, 50, 50, 30, 90, 50, 50, 50, 50, 50, 40, 50]
        data = self.indicators._rsi_convergence_predict3(data)
        self.assertEqual(data, TradeAction.BUY)


        # Teste Sell-Pfad
        data = DataFrame()
        data['high'] = [110, 110, 110, 110, 110, 130, 110, 110, 110, 110, 110, 140, 110]
        data['low'] = [90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90]
        data['RSI'] = [50,50 , 50, 50, 50, 90, 50, 50, 50, 50, 50, 60, 50]
        data = self.indicators._rsi_convergence_predict3(data)
        self.assertEqual(data, TradeAction.SELL)

        # Teste None-Pfad
        data = DataFrame()
        data['high'] = [110, 110, 110, 110, 110, 110, 110, 110, 110, 110, 110, 110, 110]
        data['low'] = [90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90]
        data['RSI'] = [50, 50, 50, 50, 30, 90, 50, 50, 50, 50, 50, 40, 50]
        data = self.indicators._rsi_convergence_predict3(data)
        self.assertEqual(data, TradeAction.NONE)

    def test_rsi_break_predict(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['RSI'] = [40,40,40,51]
        data = self.indicators._rsi_break_predict(data)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Sell-Pfad
        data = DataFrame()
        data['RSI'] = [40, 40, 60, 40]
        data = self.indicators._rsi_break_predict(data)
        self.assertEqual(data, TradeAction.SELL)

    def test_bb_crossing(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['BB_MIDDLE'] = [110, 110, 110, 110, 110, 80, 110, 110, 110, 110, 110, 70, 110]
        data['close'] = [110, 110, 110, 110, 110, 80, 110, 110, 110, 110, 70, 70, 120]
        data = self.indicators._bb_middle_cross_predict(data)
        self.assertEqual(data, TradeAction.BUY)

        data = DataFrame()
        data['BB_MIDDLE'] = [110, 110, 110, 110, 110, 80, 110, 110, 110, 110, 110, 70, 110]
        data['close'] = [110, 110, 110, 110, 110, 80, 110, 110, 110, 110, 200, 70, 90]
        data = self.indicators._bb_middle_cross_predict(data)
        self.assertEqual(data, TradeAction.SELL)




    def test_williams_break_predict(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['WILLIAMS'] = [-40, -60, -60, -40]
        data = self.indicators._williams_break_predict(data)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Sell-Pfad
        data = DataFrame()
        data['WILLIAMS'] = [-40, -40, -30, -70]
        data = self.indicators._williams_break_predict(data)
        self.assertEqual(data, TradeAction.SELL)

    def test_williams_limit_predict(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['WILLIAMS'] = [-40]
        data = self.indicators._williams_limit_predict(data)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Sell-Pfad
        data = DataFrame()
        data['WILLIAMS'] = [-70]
        data = self.indicators._williams_limit_predict(data)
        self.assertEqual(data, TradeAction.SELL)

        # Teste None-Pfad
        data = DataFrame()
        data['WILLIAMS'] = [-10]
        data = self.indicators._williams_limit_predict(data)
        self.assertEqual(data, TradeAction.NONE)

        # Teste None-Pfad
        data = DataFrame()
        data['WILLIAMS'] = [-90]
        data = self.indicators._williams_limit_predict(data)
        self.assertEqual(data, TradeAction.NONE)

    def test_rsi_predict(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['RSI'] = [51]
        data = self.indicators._rsi_predict(data)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Sell-Pfad
        data = DataFrame()
        data['RSI'] = [49]
        action = self.indicators._rsi_predict(data)
        self.assertEqual(action, TradeAction.SELL)

        # Teste None-Pfad
        data = DataFrame()
        data['RSI'] = [50]
        action = self.indicators._rsi_predict(data)
        self.assertEqual(action, TradeAction.NONE)

    def test_rsi_30_70_predict(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['RSI_SMOOTH'] = [80]
        data = self.indicators._rsi_smooth_30_70_predict(data)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Sell-Pfad
        data = DataFrame()
        data['RSI_SMOOTH'] = [20]
        action = self.indicators._rsi_smooth_30_70_predict(data)
        self.assertEqual(action, TradeAction.SELL)

        # Teste None-Pfad
        data = DataFrame()
        data['RSI_SMOOTH'] = [50]
        action = self.indicators._rsi_smooth_30_70_predict(data)
        self.assertEqual(action, TradeAction.NONE)

    def test_rsi_30_70_predict(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['RSI_SMOOTH'] = [80]
        data = self.indicators._rsi_smooth_30_70_predict(data)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Sell-Pfad
        data = DataFrame()
        data['RSI_SMOOTH'] = [20]
        action = self.indicators._rsi_smooth_30_70_predict(data)
        self.assertEqual(action, TradeAction.SELL)

        # Teste None-Pfad
        data = DataFrame()
        data['RSI_SMOOTH'] = [50]
        action = self.indicators._rsi_smooth_30_70_predict(data)
        self.assertEqual(action, TradeAction.NONE)

    def test_rsi_slope_predict(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['RSI_SMOOTH'] = [80, 80, 60, 80]
        data = self.indicators._rsi_smooth_slope_predict(data)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Sell-Pfad
        data = DataFrame()
        data['RSI_SMOOTH'] = [80, 80, 60, 50]
        action = self.indicators._rsi_smooth_slope_predict(data)
        self.assertEqual(action, TradeAction.SELL)

    def test_macd_predict(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['MACD'] = [80]
        data['SIGNAL'] = [70]
        data = self.indicators._macd_predict(data)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Sell-Pfad
        data = DataFrame()
        data['MACD'] = [80]
        data['SIGNAL'] = [90]
        action = self.indicators._macd_predict(data)
        self.assertEqual(action, TradeAction.SELL)

    def test_macd_zero_predict(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['MACD'] = [80]
        data['SIGNAL'] = [70]
        data = self.indicators._macd_predict_zero_line(data)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Sell-Pfad
        data = DataFrame()
        data['MACD'] = [-40]
        data['SIGNAL'] = [-30]
        action = self.indicators._macd_predict_zero_line(data)
        self.assertEqual(action, TradeAction.SELL)

    def test_macd_cross_predict(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['MACD'] = [80, 70, 80, 80]
        data['SIGNAL'] = [70, 80, 70, 70]
        data = self.indicators._macd_crossing_predict(data)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Sell-Pfad
        data = DataFrame()
        data['MACD'] = [80, 80, 80, 70]
        data['SIGNAL'] = [70, 70, 70, 80]
        action = self.indicators._macd_crossing_predict(data)
        self.assertEqual(action, TradeAction.SELL)

    def test_candle(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['close'] = [80]
        data['open'] = [60]
        data['high'] = [66]
        data['low'] = [66]
        data = self.indicators._candle_predict(data)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Sell-Pfad
        data = DataFrame()
        data['close'] = [60]
        data['open'] = [80]
        data['high'] = [66]
        data['low'] = [80]
        action = self.indicators._candle_predict(data)
        self.assertEqual(action, TradeAction.SELL)

    def test_macd_cross_predict(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['MACD'] = [80, 70, 80, 80]
        data['SIGNAL'] = [70, 80, 70, 70]
        data = self.indicators._macd_crossing_predict(data)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Sell-Pfad
        data = DataFrame()
        data['MACD'] = [80, 80, 80, 70]
        data['SIGNAL'] = [70, 70, 70, 80]
        action = self.indicators._macd_crossing_predict(data)
        self.assertEqual(action, TradeAction.SELL)

    def test_ichimoku_chikou(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['CHIKOU'] = [80]
        data['close'] = [70]
        data = self.indicators._ichimoku_chikou_predict(data)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Sell-Pfad
        data = DataFrame()
        data['CHIKOU'] = [80]
        data['close'] = [90]
        action = self.indicators._ichimoku_chikou_predict(data)
        self.assertEqual(action, TradeAction.SELL)

    def test_tenkan_kijun_chikou(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['TENKAN'] = [60, 70, 75, 80]
        data['KIJUN'] = [70, 70, 70, 70]
        data = self.indicators._ichimoku_tenkan_kijun_predict(data)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Sell-Pfad
        data = DataFrame()
        data['TENKAN'] = [80, 70, 60, 55]
        data['KIJUN'] = [70, 70, 70, 70]
        action = self.indicators._ichimoku_tenkan_kijun_predict(data)
        self.assertEqual(action, TradeAction.SELL)

    def test_kijun_close(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['KIJUN'] = [80]
        data['close'] = [90]
        data = self.indicators._ichimoku_kijun_close_predict(data)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Sell-Pfad
        data = DataFrame()
        data['KIJUN'] = [80]
        data['close'] = [70]
        data = self.indicators._ichimoku_kijun_close_predict(data)
        self.assertEqual(data, TradeAction.SELL)

    def test_kijun_close_cross(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['KIJUN'] = [80,80]
        data['close'] = [70,90]
        data = self.indicators._ichimoku_kijun_close_cross_predict(data)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Sell-Pfad
        data = DataFrame()
        data['KIJUN'] = [80,80]
        data['close'] = [90,70]
        data = self.indicators._ichimoku_kijun_close_cross_predict(data)
        self.assertEqual(data, TradeAction.SELL)

        data = DataFrame()
        data['KIJUN'] = [80, 80]
        data['close'] = [90, 90]
        data = self.indicators._ichimoku_kijun_close_cross_predict(data)
        self.assertEqual(data, TradeAction.NONE)

    def test_ichimoku_cloud(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['SENKOU_A'] = [80]
        data['SENKOU_B'] = [70]
        data['close'] = [90]
        data = self.indicators._ichimoku_cloud_predict(data)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Sell-Pfad
        data = DataFrame()
        data['SENKOU_A'] = [80]
        data['SENKOU_B'] = [90]
        data['close'] = [70]
        action = self.indicators._ichimoku_cloud_predict(data)
        self.assertEqual(action, TradeAction.SELL)

        # Teste None-Pfad
        data = DataFrame()
        data['SENKOU_A'] = [80]
        data['SENKOU_B'] = [90]
        data['close'] = [100]
        action = self.indicators._ichimoku_cloud_predict(data)
        self.assertEqual(action, TradeAction.NONE)

    def test_ichimoku_cloud_thickness(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['SENKOU_A'] = [60, 75, 80, 90]
        data['SENKOU_B'] = [70, 70, 70, 70]
        data = self.indicators._ichimoku_cloud_thickness_predict(data)
        self.assertEqual(data, TradeAction.BUY)

        data = DataFrame()
        data['SENKOU_A'] = [70, 70, 70, 70]
        data['SENKOU_B'] = [60, 65, 75, 80]
        data = self.indicators._ichimoku_cloud_thickness_predict(data)
        self.assertEqual(data, TradeAction.SELL)

        data = DataFrame()
        data['SENKOU_A'] = [70, 70, 70, 70]
        data['SENKOU_B'] = [70, 70, 70, 70]
        data = self.indicators._ichimoku_cloud_thickness_predict(data)
        self.assertEqual(data, TradeAction.NONE)

        data = DataFrame()
        data['SENKOU_A'] = [80, 80, 80, 71]
        data['SENKOU_B'] = [70, 70, 70, 70]
        data = self.indicators._ichimoku_cloud_thickness_predict(data)
        self.assertEqual(data, TradeAction.NONE)

        # Teste None-Pfad
        data = DataFrame()
        data['SENKOU_A'] = [80]
        data['SENKOU_B'] = [90]
        data['close'] = [100]
        action = self.indicators._ichimoku_cloud_predict(data)
        self.assertEqual(action, TradeAction.NONE)

    def test_adx(self):
        # Teste Both-Pfad
        data_both = DataFrame()
        data_both['ADX'] = [30]
        data = self.indicators._adx_predict(data_both)
        self.assertEqual(data, TradeAction.BOTH)

        # Teste Both-Pfad
        data = DataFrame()
        data['ADX'] = [10]
        action = self.indicators._adx_predict(data)
        self.assertEqual(action, TradeAction.NONE)

    def test_ema_10_50(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['EMA_10'] = [60, 75, 80, 90]
        data['EMA_50'] = [70, 70, 70, 70]
        data = self.indicators._ema_10_50_diff(data)
        self.assertEqual(data, TradeAction.BUY)

        data = DataFrame()
        data['EMA_10'] = [70, 70, 70, 70]
        data['EMA_50'] = [60, 65, 75, 80]
        data = self.indicators._ema_10_50_diff(data)
        self.assertEqual(data, TradeAction.SELL)

        data = DataFrame()
        data['EMA_10'] = [70, 70, 70, 70]
        data['EMA_50'] = [70, 70, 70, 70]
        data = self.indicators._ema_10_50_diff(data)
        self.assertEqual(data, TradeAction.NONE)

        data = DataFrame()
        data['EMA_10'] = [80, 80, 80, 71]
        data['EMA_50'] = [70, 70, 70, 70]
        data = self.indicators._ema_10_50_diff(data)
        self.assertEqual(data, TradeAction.NONE)
