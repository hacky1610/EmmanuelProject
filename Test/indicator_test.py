import unittest
from unittest.mock import MagicMock

import pandas as pd
from pandas import DataFrame

from BL.datatypes import TradeAction
from BL.indicators import Indicators, Indicator  # Stellen Sie sicher, dass Sie den richtigen Modulnamen verwenden


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
        self.dp = MagicMock()

        self.indicators = Indicators(dp=self.dp )

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

    def test_ema_hist_predict(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['EMA_10'] = [118,118,118,118]
        data['EMA_20'] = [115,115,115,115]
        data['EMA_30'] = [114,114,114,114]
        data = self.indicators._ema_hist_predict(data)
        self.assertEqual(data, TradeAction.BUY)


    def test_rsi_convergence_predict(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['high'] = [110, 110, 110, 110, 110, 110, 110, 110, 110, 110, 110, 110, 110]
        data['low'] = [90, 90, 90, 90, 30, 90, 90, 90, 90, 90, 90, 10, 90]
        data['RSI'] = [50, 50, 50, 50, 30, 90, 50, 50, 50, 50, 50, 40, 50]
        data = self.indicators._rsi_convergence_predict3(data)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Buy-Pfad
        data = DataFrame()
        data['high'] = [110, 110, 110, 110, 110, 110, 110, 110, 110, 110, 110, 110, 110]
        data['low'] = [50, 90, 90, 40, 30, 90, 90, 90, 90, 90, 90, 10, 5]
        data['RSI'] = [50, 50, 50, 50, 30, 90, 50, 50, 50, 50, 50, 40, 50]
        data = self.indicators._rsi_convergence_predict3(data)
        self.assertEqual(data, TradeAction.BUY)


        # Teste Sell-Pfad
        data = DataFrame()
        data['high'] = [110, 110, 110, 110, 110, 130, 110, 110, 110, 110, 110, 190, 110]
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
        data['RSI'] = [40, 40,40,40,51]
        data = self.indicators._rsi_break_predict(data)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Sell-Pfad
        data = DataFrame()
        data['RSI'] = [40, 40, 40, 60, 40]
        data = self.indicators._rsi_break_predict(data)
        self.assertEqual(data, TradeAction.SELL)

    def test_rsi_30_70_break_predict(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['RSI'] = [40, 40,40,20,51]
        data = self.indicators._rsi_break_30_70_predict(data)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Sell-Pfad
        data = DataFrame()
        data['RSI'] = [40, 40, 40, 90, 66]
        data = self.indicators._rsi_break_30_70_predict(data)
        self.assertEqual(data, TradeAction.SELL)

    def test_bb_middle_crossing(self):
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

    def test_slope_predict(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['EMA'] = [99,100,101,102]
        data = self.indicators._check_slope(data['EMA'])
        self.assertEqual(data, TradeAction.BUY)

        data = DataFrame()
        data['EMA'] = [99, 100, 80, 102]
        data = self.indicators._check_slope(data['EMA'])
        self.assertEqual(data, TradeAction.NONE)

        data = DataFrame()
        data['EMA'] = [110, 109, 108, 107]
        data = self.indicators._check_slope(data['EMA'])
        self.assertEqual(data, TradeAction.SELL)


    def test_williams_break_predict(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['WILLIAMS'] = [-40, -40, -60, -60, -40]
        data = self.indicators._williams_break_predict(data)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Sell-Pfad
        data = DataFrame()
        data['WILLIAMS'] = [-40, -40, -40, -30, -70]
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

    def test_rsi_slope_predict_2(self):
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

    def test_macd_max_predict(self):
        # Teste None-Pfad
        data = DataFrame()
        data['MACD'] = [80, 60, 60, 75]
        data = self.indicators._macd_max_predict(data)
        self.assertEqual(data, TradeAction.NONE)

        # Teste None-Pfad
        data = DataFrame()
        data['MACD'] = [-80, -60, -60, -75]
        data = self.indicators._macd_max_predict(data)
        self.assertEqual(data, TradeAction.NONE)

        # Teste Both-Pfad
        data = DataFrame()
        data['MACD'] = [80, 60, 60, 61]
        data = self.indicators._macd_max_predict(data)
        self.assertEqual(data, TradeAction.BOTH)

        # Teste None-Pfad
        data = DataFrame()
        data['MACD'] = [80, 60, 60, 90]
        data = self.indicators._macd_max_predict(data)
        self.assertEqual(data, TradeAction.NONE)



    def test_macd_signal_diff_predict(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['MACD'] = [80, 83]
        data['SIGNAL'] = [70, 70]
        data = self.indicators._macd_signal_diff_predict(data)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Buy-Pfad
        data = DataFrame()
        data['MACD'] = [60, 55]
        data['SIGNAL'] = [70, 70]
        data = self.indicators._macd_signal_diff_predict(data)
        self.assertEqual(data, TradeAction.SELL)

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

    def test_candle_pattern(self):
        # Teste None-Pfad
        data = DataFrame()
        data['close'] = [80]
        data['open'] = [60]
        data['high'] = [66]
        data['low'] = [66]
        data = self.indicators._candle_pattern_predict(data)
        self.assertEqual(data, TradeAction.NONE)

        data = DataFrame()
        data['close'] = [80,90,90,90]
        data['open'] = [80,90,90,90]
        data['high'] = [80,90,90,90]
        data['low'] = [80,90,90,90]
        data = self.indicators._candle_pattern_predict(data)
        self.assertEqual(data, TradeAction.NONE)



    def test_macd_cross_predict_2(self):
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



    def test_tenkan_kijun_chikou_2(self):
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

    def test_max_adx(self):
        # Teste Both-Pfad
        data_both = DataFrame()
        data_both['ADX'] = [40,40,30]
        data = self.indicators._adx_max_predict(data_both)
        self.assertEqual(data, TradeAction.BOTH)

        # Teste Both-Pfad
        data_both = DataFrame()
        data_both['ADX'] = [29, 31, 30]
        data = self.indicators._adx_max_predict(data_both)
        self.assertEqual(data, TradeAction.NONE)

    def test_macd_slope(self):
        # Teste Buy-Pfad
        data_both = DataFrame()
        data_both['MACD'] = [100,100,101]
        data = self.indicators._macd_slope_predict(data_both)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Buy-Pfad
        data_both = DataFrame()
        data_both['MACD'] = [100, 100, 90]
        data = self.indicators._macd_slope_predict(data_both)
        self.assertEqual(data, TradeAction.SELL)

        # Teste None-Pfad
        data_both = DataFrame()
        data_both['MACD'] = [90]
        data = self.indicators._macd_slope_predict(data_both)
        self.assertEqual(data, TradeAction.NONE)

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

    def test_ema_10_30_diff_max(self):
        # Teste None-Pfad
        data = DataFrame()
        data['EMA_10'] = [100,60, 75, 80, 90]
        data['EMA_30'] = [80,70, 70, 70, 70]
        data = self.indicators._ema_10_30_diff_max(data)
        self.assertEqual(data, TradeAction.NONE)

        # Teste Both-Pfad
        data = DataFrame()
        data['EMA_10'] = [100, 60, 75, 80, 90]
        data['EMA_30'] = [80, 70, 70, 70, 80]
        data = self.indicators._ema_10_30_diff_max(data)
        self.assertEqual(data, TradeAction.BOTH)



    def test_ema_20_channel(self):
        data = DataFrame()
        data['EMA_20_HIGH'] = [100, 100, 100, 100]
        data['EMA_20_LOW'] = [80, 80, 80, 80]
        data = self.indicators._ema_20_channel(data)
        self.assertEqual(data, TradeAction.NONE)

        data = DataFrame()
        data['EMA_20_HIGH'] = [100, 100, 100, 100, 100]
        data['high'] = [100, 100, 100, 110, 100]
        data['close'] = [100, 100, 100, 100, 100]
        data['low'] = [100, 100, 100, 60, 100]
        data['EMA_20_LOW'] = [80, 80, 80, 80, 80]
        data = self.indicators._ema_20_channel(data)
        self.assertEqual(data, TradeAction.BUY)

        data = DataFrame()
        data['EMA_20_HIGH'] = [100, 100, 100, 100, 100]
        data['high'] = [90, 90, 90, 110, 100]
        data['close'] = [60, 60, 60, 100, 60]
        data['low'] = [100, 100, 100, 100, 100]
        data['EMA_20_LOW'] = [80, 80, 80, 80, 80]
        data = self.indicators._ema_20_channel(data)
        self.assertEqual(data, TradeAction.SELL)



    def test_ema_20_close(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['EMA_20'] = [60, 75, 80, 90]
        data['close'] = [70, 70, 90, 100]
        data = self.indicators._ema_20_close(data)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Sell-Pfad
        data = DataFrame()
        data['EMA_20'] = [60, 75, 80, 90]
        data['close'] = [70, 70, 50, 50]
        data = self.indicators._ema_20_close(data)
        self.assertEqual(data, TradeAction.SELL)

        # Teste None Pfad
        data = DataFrame()
        data['EMA_20'] = [60, 75, 80, 90]
        data['close'] = [70, 70, 50, 100]
        data = self.indicators._ema_20_close(data)
        self.assertEqual(data, TradeAction.NONE)

    def test_smma_20_close(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['SMMA_20'] = [60, 75, 80, 90]
        data['close'] = [70, 70, 90, 100]
        data = self.indicators._smma_20_close(data)
        self.assertEqual(data, TradeAction.BUY)

        # Teste Sell-Pfad
        data = DataFrame()
        data['SMMA_20'] = [60, 75, 80, 90]
        data['close'] = [70, 70, 50, 50]
        data = self.indicators._smma_20_close(data)
        self.assertEqual(data, TradeAction.SELL)

        # Teste None Pfad
        data = DataFrame()
        data['SMMA_20'] = [60, 75, 80, 90]
        data['close'] = [70, 70, 50, 100]
        data = self.indicators._smma_20_close(data)
        self.assertEqual(data, TradeAction.NONE)


    def test_ema_20_smma_20(self):
        # Teste Buy-Pfad
        data = DataFrame()
        data['SMMA_20'] = [60, 75, 80, 90]
        data['EMA_20'] = [70, 70, 100, 100]
        data = self.indicators._ema_20_smma_20(data)
        self.assertEqual(data, TradeAction.BUY)


    def sample_dataframe_buy(self):
        """Erstellt einen Beispiel-DataFrame mit Hoch- und Tiefpunkten sowie einem Indikator."""
        data =  {
        "low":         [-4, -5, 0, 0, 0, 0, 0, 0, -10, 0],
        "high":        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "pivot_point": [1, 1, 0, 0, 0, 0, 0, 0, 1, 0],  # Hochs = 3, Tiefs = 1
        "indicator":   [1, 1, 5, 5, 5, 5, 5, 5, 5, 0],  # Indikator schwankt
        }
        df = pd.DataFrame(data)
        return df

    def sample_dataframe_hidden_stength_buy(self):
        """Erstellt einen Beispiel-DataFrame mit Hoch- und Tiefpunkten sowie einem Indikator."""
        data =  {
        "low":         [-8, -5, 0, 0, 0, 0, 0, 0, -3, 0],
        "high":        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "pivot_point": [1, 1, 0, 0, 0, 0, 0, 0, 1, 0],  # Hochs = 3, Tiefs = 1
        "indicator":   [20, 10, 5, 5, 5, 5, 5, 5, 5, 0],  # Indikator schwankt
        }
        df = pd.DataFrame(data)
        return df

    def sample_dataframe_hidden_stength_sell(self):
        """Erstellt einen Beispiel-DataFrame mit Hoch- und Tiefpunkten sowie einem Indikator."""
        data =  {
        "low":         [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "high":        [12, 10, 0, 0, 0, 0, 0, 0, 0, 7],
        "pivot_point": [2, 2, 0, 0, 0, 0, 0, 0, 0, 2],  # Hochs = 3, Tiefs = 1
        "indicator":   [20, 50, 5, 5, 5, 5, 5, 5, 5, 100],  # Indikator schwankt
        }
        df = pd.DataFrame(data)
        return df

    def sample_dataframe_none(self):
        """Erstellt einen Beispiel-DataFrame mit Hoch- und Tiefpunkten sowie einem Indikator."""
        data = {
            "low": [0, -1, 0, -1, 0, 0, 0, 0, 0, 0],
            "high": [0, 0, 0, 0, 0, 0, 0, 0, 0, 2],
            "pivot_point": [0, 1, 0, 1, 0, 0, 0, 0, 0, 2],  # Hochs = 3, Tiefs = 1
            "indicator": [5, 0, 5, 5, 5, 5, 5, 5, 5, 10],  # Indikator schwankt
        }
        df = pd.DataFrame(data)
        return df

    def sample_dataframe_sell(self):
        """Erstellt einen Beispiel-DataFrame mit Hoch- und Tiefpunkten sowie einem Indikator."""
        data = {
            "low": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            "high": [0, 10, 9, 0, 0, 0, 0, 0, 100, 0],
            "pivot_point": [0, 2, 2, 0, 0, 0, 0, 0, 2, 0],  # Hochs = 3, Tiefs = 1
            "indicator": [5, 30, 30, 5, 5, 5, 5, 5, 20, 5],  # Indikator schwankt
        }
        df = pd.DataFrame(data)
        return df

    def test_convergence_predict_sell(self):

        df = self.sample_dataframe_sell()
        result = self.indicators._convergence_predict(df, "indicator", pv=MagicMock())
        assert result == TradeAction.SELL, f"Erwartet: SELL, erhalten: {result}"

    def test_convergence_predict_buy(self):
        """Testet, ob ein BUY-Signal korrekt erkannt wird."""
        df = self.sample_dataframe_buy()
        result = self.indicators._convergence_predict(df, "indicator", pv=MagicMock())
        assert result == TradeAction.BUY, f"Erwartet: BUY, erhalten: {result}"

    def test_convergence_predict_none(self):
        """Testet, ob die Funktion korrekt NONE zurückgibt, wenn kein Signal vorliegt."""
        df = self.sample_dataframe_none()
        result = self.indicators._convergence_predict(df, "indicator", pv=MagicMock())
        assert result == TradeAction.NONE, f"Erwartet: BUY, erhalten: {result}"

    def test_fake_breakdown_buy(self):
        """Testet, ob ein BUY-Signal korrekt erkannt wird."""
        df = self.sample_dataframe_hidden_stength_buy()
        result = self.indicators._hidden_stength_breakdown(df, "indicator", pv=MagicMock())
        assert result == TradeAction.BUY, f"Erwartet: BUY, erhalten: {result}"

    def test_fake_breakdown_sell(self):
        """Testet, ob ein BUY-Signal korrekt erkannt wird."""
        df = self.sample_dataframe_hidden_stength_sell()
        result = self.indicators._hidden_stength_breakdown(df, "indicator", pv=MagicMock())
        assert result == TradeAction.SELL, f"Erwartet: SELL, erhalten: {result}"

    def test_predict_returns_none_when_max_none_exceeded(self):
        result = self.indicators._predict(
            predict_values=[TradeAction.NONE, TradeAction.NONE, TradeAction.BUY],
            max_none=1
        )
        self.assertEqual(result, TradeAction.NONE)

    def test_predict_returns_both_when_all_values_are_both(self):
        result = self.indicators._predict(
            predict_values=[TradeAction.BOTH, TradeAction.BOTH, TradeAction.BOTH],
            max_none=0
        )
        self.assertEqual(result, TradeAction.BOTH)

    def test_predict_returns_buy_when_majority_is_buy_or_both(self):
        result = self.indicators._predict(
            predict_values=[TradeAction.BUY, TradeAction.BOTH, TradeAction.NONE],
            max_none=1
        )
        self.assertEqual(result, TradeAction.BUY)

    def test_predict_returns_sell_when_majority_is_sell_or_both(self):
        result = self.indicators._predict(
            predict_values=[TradeAction.SELL, TradeAction.BOTH, TradeAction.NONE],
            max_none=1
        )
        self.assertEqual(result, TradeAction.SELL)

    def test_predict_returns_none_when_no_majority(self):
        result = self.indicators._predict(
            predict_values=[TradeAction.BUY, TradeAction.SELL, TradeAction.NONE],
            max_none=1
        )
        self.assertEqual(result, TradeAction.NONE)

    def test_predict_some_returns_correct_action_for_multiple_indicators(self):
        indicators = Indicators()
        indicators._get_indicators_by_names = MagicMock(return_value=[
            Indicator("mock1", lambda df: TradeAction.BUY),
            Indicator("mock2", lambda df: TradeAction.SELL),
            Indicator("mock3", lambda df: TradeAction.NONE)
        ])
        result = indicators.predict_some(None, ["mock1", "mock2", "mock3"], max_none=1)
        self.assertEqual(result, TradeAction.NONE)

    def test_predict_some_returns_none_when_max_none_exceeded(self):
        indicators = Indicators()
        indicators._get_indicators_by_names = MagicMock(return_value=[
            Indicator("mock1", lambda df: TradeAction.NONE),
            Indicator("mock2", lambda df: TradeAction.NONE),
            Indicator("mock3", lambda df: TradeAction.BUY)
        ])
        result = indicators.predict_some(None, ["mock1", "mock2", "mock3"], max_none=1)
        self.assertEqual(result, TradeAction.NONE)

    def test_predict_single_returns_correct_action_for_single_indicator(self):
        indicators = Indicators()
        indicators._get_indicator_by_name = MagicMock(return_value=Indicator("mock", lambda df: TradeAction.BUY))
        result = indicators.predict_single(None, "mock")
        self.assertEqual(result, TradeAction.BUY)
















