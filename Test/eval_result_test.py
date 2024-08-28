import unittest
from unittest.mock import MagicMock
from BL.analytics import Analytics
from BL.datatypes import TradeAction
from BL.eval_result import EvalResultCollection, TradeResult, EvalResult
from BL.indicators import Indicators
from Connectors.market_store import Market
from Predictors.base_predictor import BasePredictor
from pandas import DataFrame, Series

class TestEvalResult(unittest.TestCase):

    def test_is_better_returns_true_when_compare_to_has_higher_wl(self):
        eval1 = EvalResult()
        eval2 = EvalResult()
        eval1.get_win_loss = MagicMock(return_value=0.6)
        eval2.get_win_loss = MagicMock(return_value=0.9)
        self.assertTrue(eval1.is_better(eval2))

    def test_is_better_returns_false_when_self_has_higher_wl(self):
        eval1 = EvalResult()
        eval2 = EvalResult()
        eval1.get_win_loss = MagicMock(return_value=0.6)
        eval2.get_win_loss = MagicMock(return_value=0.3)
        self.assertFalse(eval1.is_better(eval2))

    def test_is_better_returns_true_when_compare_to_has_higher_reward(self):
        eval1 = EvalResult()
        eval2 = EvalResult()
        eval1.get_win_loss = MagicMock(return_value=0.8)
        eval2.get_win_loss = MagicMock(return_value=0.81)
        eval1.get_reward = MagicMock(return_value=100)
        eval2.get_reward = MagicMock(return_value=300)
        self.assertTrue(eval1.is_better(eval2))

    def test_is_better_returns_false_when_self_has_higher_win_loss_and_over_08(self):
        eval1 = EvalResult()
        eval2 = EvalResult()
        eval1.get_win_loss = MagicMock(return_value=0.9)
        eval2.get_win_loss = MagicMock(return_value=0.81)
        self.assertFalse(eval1.is_better(eval2))

    def test_is_better_returns_false_when_wl_same_and_reward_better(self):
        eval1 = EvalResult()
        eval2 = EvalResult()
        eval1.get_win_loss = MagicMock(return_value=0.4)
        eval2.get_win_loss = MagicMock(return_value=0.4)
        eval1.get_reward = MagicMock(return_value=400)
        eval2.get_reward = MagicMock(return_value=300)
        self.assertFalse(eval1.is_better(eval2))


