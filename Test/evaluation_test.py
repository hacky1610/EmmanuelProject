import unittest
from unittest.mock import MagicMock
from Connectors.tiingo import Tiingo
from BL.analytics import Analytics
from Predictors.rsi_bb import RsiBB
from pandas import DataFrame, Series


class EvaluationTest(unittest.TestCase):

    def setUp(self):
        self.a = Analytics()

    def add_line(self, df: DataFrame, date, close, low, high, rsi, bb_lower, bb_middle, bb_upper):
        return df.append(
            Series([close,low, high, rsi, bb_lower, bb_middle, bb_upper,date],
                   index=["close","low", "high", "RSI", "BB_LOWER", "BB_MIDDLE", "BB_UPPER", "date"]),
            ignore_index=True)

    def predict_mock(self):

    def test_no_trades(self):
        p = MagicMock(side_effect=)

        df = DataFrame()
        df = self.add_line(df, "2023-01-01T25:00:00.00Z",900, 900, 901, 50, 800, 900, 1000)
        df = self.add_line(df, "2023-01-01T16:00:00.00Z",900, 900, 901, 50, 800, 900, 1000)
        df = self.add_line(df, "2023-01-01T17:00:00.00Z",900, 900, 901, 50, 800, 900, 1000)
        df = self.add_line(df, "2023-01-01T18:00:00.00Z",900, 900, 901, 50, 800, 900, 1000)
        df = self.add_line(df, "2023-01-01T19:00:00.00Z",900, 900, 901, 50, 800, 900, 1000)
        df = self.add_line(df,"2023-01-01T20:00:00.00Z",900, 900, 901, 50, 800, 900, 1000)

        df_eval = DataFrame()
        df_eval = self.add_line(df_eval, "2023-01-01T19:00:00.00Z",900, 900, 901, 50, 800, 900, 1000)
        df_eval = self.add_line(df_eval, "2023-01-01T19:05:00.00Z",900, 900, 901, 50, 800, 900, 1000)
        df_eval = self.add_line(df_eval, "2023-01-01T19:10:00.00Z",900, 900, 901, 50, 800, 900, 1000)
        df_eval = self.add_line(df_eval, "2023-01-01T19:15:00.00Z",900, 900, 901, 50, 800, 900, 1000)
        df_eval = self.add_line(df_eval, "2023-01-01T19:20:00.00Z",900, 900, 901, 50, 800, 900, 1000)
        df_eval = self.add_line(df_eval, "2023-01-01T19:25:00.00Z",900, 900, 901, 50, 800, 900, 1000)
        reward, avg_reward, trade_freq, win_loss, avg_min, trades = self.a.evaluate(p,df,df_eval)

        assert reward == 0

    def test_buy_won_trade(self):
        p = RsiBB()
        p.get_stop_limit = MagicMock(return_value=(10,10))

        df = DataFrame()
        df = self.add_line(df,"2023-01-01T13:00:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df = self.add_line(df,"2023-01-01T14:00:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df = self.add_line(df,"2023-01-01T15:00:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df = self.add_line(df,"2023-01-01T16:00:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df = self.add_line(df,"2023-01-01T17:00:00.00Z", 900, 900, 901, 50, 800, 1050, 1000)
        df = self.add_line(df,"2023-01-01T18:00:00.00Z", 900, 900, 901, 50, 800, 1000, 1000)
        df = self.add_line(df,"2023-01-01T19:00:00.00Z", 900, 900, 901, 50, 800, 950, 1000)
        df = self.add_line(df,"2023-01-01T20:00:00.00Z", 900, 700, 901, 20, 800, 900, 1000)

        df_eval = DataFrame()
        df_eval = self.add_line(df_eval, "2023-01-01T21:00:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df_eval = self.add_line(df_eval, "2023-01-01T21:05:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df_eval = self.add_line(df_eval, "2023-01-01T21:10:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df_eval = self.add_line(df_eval, "2023-01-01T21:15:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df_eval = self.add_line(df_eval, "2023-01-01T21:20:00.00Z", 900, 900, 911, 50, 800, 900, 1000)
        df_eval = self.add_line(df_eval, "2023-01-01T21:25:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        reward, avg_reward, trade_freq, win_loss, avg_min, trades = self.a.evaluate(p, df, df_eval)

        assert win_loss == 1.0
        assert reward == 10
        assert avg_reward == 10

    def test_buy_lost_trade(self):
        p = RsiBB()
        p.get_stop_limit = MagicMock(return_value=(10,10))

        df = DataFrame()
        df = self.add_line(df,"2023-01-01T13:00:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df = self.add_line(df,"2023-01-01T14:00:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df = self.add_line(df,"2023-01-01T15:00:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df = self.add_line(df,"2023-01-01T16:00:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df = self.add_line(df,"2023-01-01T17:00:00.00Z", 900, 900, 901, 50, 800, 1050, 1000)
        df = self.add_line(df,"2023-01-01T18:00:00.00Z", 900, 900, 901, 50, 800, 1000, 1000)
        df = self.add_line(df,"2023-01-01T19:00:00.00Z", 900, 900, 901, 50, 800, 950, 1000)
        df = self.add_line(df,"2023-01-01T20:00:00.00Z", 900, 700, 901, 20, 800, 900, 1000)

        df_eval = DataFrame()
        df_eval = self.add_line(df_eval, "2023-01-01T21:00:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df_eval = self.add_line(df_eval, "2023-01-01T21:05:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df_eval = self.add_line(df_eval, "2023-01-01T21:10:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df_eval = self.add_line(df_eval, "2023-01-01T21:15:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df_eval = self.add_line(df_eval, "2023-01-01T21:20:00.00Z", 900, 800, 901, 50, 800, 900, 1000)
        df_eval = self.add_line(df_eval, "2023-01-01T21:25:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        reward, avg_reward, trade_freq, win_loss, avg_min,trades = self.a.evaluate(p, df, df_eval)

        assert win_loss == 0.0
        assert reward == -10

    def test_sell_won_trade(self):
        p = RsiBB()
        p.get_stop_limit = MagicMock(return_value=(10,10))

        df = DataFrame()
        df = self.add_line(df,"2023-01-01T13:00:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df = self.add_line(df,"2023-01-01T14:00:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df = self.add_line(df,"2023-01-01T15:00:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df = self.add_line(df,"2023-01-01T16:00:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df = self.add_line(df,"2023-01-01T17:00:00.00Z", 900, 900, 901, 50, 800, 1050, 1000)
        df = self.add_line(df,"2023-01-01T18:00:00.00Z", 900, 900, 901, 50, 800, 1000, 1000)
        df = self.add_line(df,"2023-01-01T19:00:00.00Z", 900, 900, 901, 50, 800, 950, 1000)
        df = self.add_line(df,"2023-01-01T20:00:00.00Z", 900, 900, 1051, 90, 800, 900, 1000)

        df_eval = DataFrame()
        df_eval = self.add_line(df_eval, "2023-01-01T21:00:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df_eval = self.add_line(df_eval, "2023-01-01T21:05:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df_eval = self.add_line(df_eval, "2023-01-01T21:10:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df_eval = self.add_line(df_eval, "2023-01-01T21:15:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df_eval = self.add_line(df_eval, "2023-01-01T21:20:00.00Z", 900, 800, 901, 50, 800, 900, 1000)
        df_eval = self.add_line(df_eval, "2023-01-01T21:25:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        reward, avg_reward, trade_freq, win_loss, avg_min, trades = self.a.evaluate(p, df, df_eval)

        assert win_loss == 1.0
        assert reward == 10
        assert avg_reward == 10

    def test_sell_lost_trade(self):
        p = RsiBB()
        p.get_stop_limit = MagicMock(return_value=(10,10))

        df = DataFrame()
        df = self.add_line(df, "2023-01-01T13:00:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df = self.add_line(df, "2023-01-01T14:00:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df = self.add_line(df, "2023-01-01T15:00:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df = self.add_line(df, "2023-01-01T16:00:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df = self.add_line(df, "2023-01-01T17:00:00.00Z", 900, 900, 901, 50, 800, 1050, 1000)
        df = self.add_line(df, "2023-01-01T18:00:00.00Z", 900, 900, 901, 50, 800, 1000, 1000)
        df = self.add_line(df, "2023-01-01T19:00:00.00Z", 900, 900, 901, 50, 800, 950, 1000)
        df = self.add_line(df, "2023-01-01T20:00:00.00Z", 900, 900, 1051, 90, 800, 900, 1000)

        df_eval = DataFrame()
        df_eval = self.add_line(df_eval, "2023-01-01T21:00:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df_eval = self.add_line(df_eval, "2023-01-01T21:05:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df_eval = self.add_line(df_eval, "2023-01-01T21:10:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df_eval = self.add_line(df_eval, "2023-01-01T21:15:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        df_eval = self.add_line(df_eval, "2023-01-01T21:20:00.00Z", 900, 900, 1051, 50, 800, 900, 1000)
        df_eval = self.add_line(df_eval, "2023-01-01T21:25:00.00Z", 900, 900, 901, 50, 800, 900, 1000)
        reward, avg_reward, trade_freq, win_loss, avg_min, trades = self.a.evaluate(p, df, df_eval)

        assert win_loss == 0.0
        assert reward == -10