import unittest
from unittest.mock import MagicMock
from BL.analytics import Analytics
from BL.datatypes import TradeAction
from BL.eval_result import EvalResultCollection
from BL.indicators import Indicators
from Connectors.market_store import Market
from Predictors.base_predictor import BasePredictor
from pandas import DataFrame, Series


class EvaluationTest(unittest.TestCase):

    def setUp(self):
        ms = MagicMock()
        ms.get_market.return_value = Market("foo",1)
        self.a = Analytics(ms, MagicMock())
        self.a._create_additional_info = MagicMock()
        self.predictor = BasePredictor("",Indicators())
        self.predictor.predict = MagicMock(side_effect=self.predict_mock)
        self.predictor.get_stop_limit = MagicMock(return_value=(10,10))

    def add_line(self, df: DataFrame, date, open, high, low, close, action=TradeAction.NONE):
        return df.append(
            Series([open, high, low, close, date, action],
                   index=["open", "high", "low", "close", "date", "action"]),
            ignore_index=True)

    def predict_mock(self, df):
        return df[-1:].action.item()

    def test_no_trades(self):

        df = DataFrame()
        df = self.add_line(df, "2023-01-01T25:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T16:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T17:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T18:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T19:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T20:00:00.00Z", 900, 950, 850, 900)

        df_eval = DataFrame()
        df_eval = self.add_line(df_eval, "2023-01-01T19:00:00.00Z", 900, 950, 850, 900)
        df_eval = self.add_line(df_eval, "2023-01-01T19:05:00.00Z", 900, 950, 850, 900)
        df_eval = self.add_line(df_eval, "2023-01-01T19:10:00.00Z", 900, 950, 850, 900)
        df_eval = self.add_line(df_eval, "2023-01-01T19:15:00.00Z", 900, 950, 850, 900)
        df_eval = self.add_line(df_eval, "2023-01-01T19:20:00.00Z", 900, 950, 850, 900)
        df_eval = self.add_line(df_eval, "2023-01-01T19:25:00.00Z", 900, 950, 850, 900)
        res = self.a.evaluate(self.predictor, df, df_eval, symbol="f", scaling=1)

        assert res.get_reward() == 0

    def test_buy_won_trade(self):

        df = DataFrame()
        df = self.add_line(df, "2023-01-01T13:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T14:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T15:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T16:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T17:00:00.00Z", 900, 900, 900, 901, action=TradeAction.BUY)
        df = self.add_line(df, "2023-01-01T18:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T19:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T20:00:00.00Z", 900, 950, 850, 900)

        df_eval = DataFrame()
        df_eval = self.add_line(df_eval, "2023-01-01T21:00:00.00Z", 900, 950, 850, 900)
        df_eval = self.add_line(df_eval, "2023-01-01T21:05:00.00Z", 900, 950, 850, 900)
        df_eval = self.add_line(df_eval, "2023-01-01T21:10:00.00Z", 900, 950, 850, 900)
        df_eval = self.add_line(df_eval, "2023-01-01T21:15:00.00Z", 900, 950, 850, 900)
        df_eval = self.add_line(df_eval, "2023-01-01T21:20:00.00Z", 900, 950, 850, 920)
        df_eval = self.add_line(df_eval, "2023-01-01T21:25:00.00Z", 900, 950, 850, 900)
        res  = self.a.evaluate(self.predictor, df, df_eval, symbol="Foo", scaling=1)

        assert res.get_win_loss() == 1.0
        assert res.get_reward() == 10
        assert res.get_average_reward() == 10

    def test_buy_lost_trade(self):

        df = DataFrame()
        df = self.add_line(df, "2023-01-01T13:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T14:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T15:00:00.00Z", 900, 950, 850, 900, action=TradeAction.BUY)
        df = self.add_line(df, "2023-01-01T16:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T17:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T18:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T19:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T20:00:00.00Z", 900, 950, 850, 900)

        df_eval = DataFrame()
        df_eval = self.add_line(df_eval, "2023-01-01T21:00:00.00Z", 900, 900, 900, 900)
        df_eval = self.add_line(df_eval, "2023-01-01T21:05:00.00Z", 900, 900, 900, 900)
        df_eval = self.add_line(df_eval, "2023-01-01T21:10:00.00Z", 900, 900, 900, 900)
        df_eval = self.add_line(df_eval, "2023-01-01T21:15:00.00Z", 900, 900, 900, 900)
        df_eval = self.add_line(df_eval, "2023-01-01T21:20:00.00Z", 900, 900, 850, 900)
        df_eval = self.add_line(df_eval, "2023-01-01T21:25:00.00Z", 900, 900, 850, 900)
        res = self.a.evaluate(self.predictor, df, df_eval,symbol="USDEUR", scaling=1)

        assert res.get_win_loss() == 0.0
        assert res.get_reward() == -20

    def sell_won_trade(self):

        df = DataFrame()
        df = self.add_line(df, "2023-01-01T13:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T14:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T15:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T16:00:00.00Z", 900, 950, 850, 900, action=TradeAction.SELL)
        df = self.add_line(df, "2023-01-01T17:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T18:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T19:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T20:00:00.00Z", 900, 950, 850, 900)

        df_eval = DataFrame()
        df_eval = self.add_line(df_eval, "2023-01-01T21:00:00.00Z", 900, 900, 900, 900)
        df_eval = self.add_line(df_eval, "2023-01-01T21:05:00.00Z", 900, 900, 900, 900)
        df_eval = self.add_line(df_eval, "2023-01-01T21:10:00.00Z", 900, 900, 900, 900)
        df_eval = self.add_line(df_eval, "2023-01-01T21:15:00.00Z", 900, 900, 900, 900)
        df_eval = self.add_line(df_eval, "2023-01-01T21:20:00.00Z", 900, 900, 900, 900)
        df_eval = self.add_line(df_eval, "2023-01-01T21:25:00.00Z", 900, 900, 850, 900)
        res = self.a.evaluate(self.predictor, df, df_eval,symbol="Foo", scaling=1)

        assert res.get_win_loss() == 1.0
        assert res.get_reward() == 50
        assert res.get_average_reward() == 50

    def sell_lost_trade(self):

        df = DataFrame()
        df = self.add_line(df, "2023-01-01T13:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T14:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T15:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T16:00:00.00Z", 900, 950, 850, 900, action=TradeAction.SELL)
        df = self.add_line(df, "2023-01-01T17:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T18:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T19:00:00.00Z", 900, 950, 850, 900)
        df = self.add_line(df, "2023-01-01T20:00:00.00Z", 900, 950, 850, 900)

        df_eval = DataFrame()
        df_eval = self.add_line(df_eval, "2023-01-01T21:00:00.00Z", 900, 900, 900, 900)
        df_eval = self.add_line(df_eval, "2023-01-01T21:05:00.00Z", 900, 900, 900, 900)
        df_eval = self.add_line(df_eval, "2023-01-01T21:10:00.00Z", 900, 900, 900, 900)
        df_eval = self.add_line(df_eval, "2023-01-01T21:15:00.00Z", 900, 900, 900, 900)
        df_eval = self.add_line(df_eval, "2023-01-01T21:20:00.00Z", 900, 930, 900, 900)
        df_eval = self.add_line(df_eval, "2023-01-01T21:25:00.00Z", 900, 900, 900, 900)
        res = self.a.evaluate(self.predictor, df, df_eval, symbol="foo", scaling=1)

        assert res.get_win_loss() == 0.0
        assert res.get_reward() == -30

    def evalresult_collection(self):

        d1 = DataFrame()
        d1 = d1.append(Series(index=["chart_index", "result", "action"], data=[1,10,"buy"]), ignore_index=True)
        d1 = d1.append(Series(index=["chart_index", "result", "action"], data=[2,10,"buy"]), ignore_index=True)

        d2 = DataFrame()
        d2 = d2.append(Series(index=["chart_index", "result", "action"], data=[1, 10, "buy"]), ignore_index=True)
        d2 = d2.append(Series(index=["chart_index", "result", "action"], data=[2, 10, "buy"]), ignore_index=True)

        result = EvalResultCollection.calc_combination([d1,d2])
        assert result == 20


        d1 = DataFrame()
        d1 = d1.append(Series(index=["chart_index", "result", "action"], data=[2, 10, "buy"]), ignore_index=True)

        d2 = DataFrame()
        d2 = d2.append(Series(index=["chart_index", "result", "action"], data=[1, 10, "buy"]), ignore_index=True)
        d2 = d2.append(Series(index=["chart_index", "result", "action"], data=[2, 10, "buy"]), ignore_index=True)

        result = EvalResultCollection.calc_combination([d1, d2])

        assert result == 10

        d1 = DataFrame()
        d1 = d1.append(Series(index=["chart_index", "result", "action"], data=[1, 10, "none"]), ignore_index=True)
        d1 = d1.append(Series(index=["chart_index", "result", "action"], data=[2, 10, "buy"]), ignore_index=True)

        d2 = DataFrame()
        d2 = d2.append(Series(index=["chart_index", "result", "action"], data=[1, 10, "buy"]), ignore_index=True)
        d2 = d2.append(Series(index=["chart_index", "result", "action"], data=[2, 10, "buy"]), ignore_index=True)

        result = EvalResultCollection.calc_combination([d1, d2])
        assert result == 20

        d1 = DataFrame()
        d1 = d1.append(Series(index=["chart_index", "result", "action"], data=[1, 10, "none"]), ignore_index=True)
        d1 = d1.append(Series(index=["chart_index", "result", "action"], data=[2, 10, "buy"]), ignore_index=True)

        d2 = DataFrame()
        d2 = d2.append(Series(index=["chart_index", "result", "action"], data=[4, 10, "buy"]), ignore_index=True)
        d2 = d2.append(Series(index=["chart_index", "result", "action"], data=[5, 10, "buy"]), ignore_index=True)

        result = EvalResultCollection.calc_combination([d1, d2])
        assert result == 0


