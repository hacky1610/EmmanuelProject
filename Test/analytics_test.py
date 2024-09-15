import unittest
from unittest.mock import Mock, patch, MagicMock

import pandas as pd
from pandas import DataFrame
from BL.analytics import Analytics
from BL.datatypes import TradeAction
from BL.eval_result import EvalResult
from datetime import datetime

class TestAnalytics(unittest.TestCase):


    def setUp(self):
        self._ig = MagicMock()
        self._ig.get_stop_distance = MagicMock(return_value=(1,False))
        self._analytics = Analytics(MagicMock(),self._ig)

    @patch('BL.analytics.MarketStore')
    @patch('BL.analytics.BaseViewer')
    def test_evaluate_action_is_mone(self, MockBaseViewer, MockMarketStore):
        # Mocking the necessary objects
        mock_predictor = Mock()
        mock_predictor._stop = 1
        mock_predictor._limit = 1
        mock_predictor.predict.return_value = TradeAction.NONE
        mock_market = Mock()
        mock_market.get_pip_value.return_value = 1
        mock_market.pip_euro = 1
        mock_market_store = MockMarketStore.return_value
        mock_market_store.get_market.return_value = mock_market
        mock_viewer = MockBaseViewer.return_value

        # Creating a non-empty DataFrame
        df = DataFrame({'date': [datetime(2024,1,1, 10), datetime(2024,1,1, 11)], 'open': [1.0, 1.0], 'close': [2.0,2.0]})
        df_eval = DataFrame({'date': [datetime.now()], 'high': [1.0], 'low': [1.0]})

        analytics = Analytics(mock_market_store,self._ig)
        result = analytics.evaluate(mock_predictor, df, df_eval, 'symbol',"epic", 1, mock_viewer)

        self.assertIsInstance(result, EvalResult)
        self.assertEqual(result.get_trades(), 0)
        self.assertEqual(result.get_win_loss(), 0)
        self.assertEqual(result.get_average_reward(), 0)

    @patch('BL.analytics.MarketStore')
    @patch('BL.analytics.BaseViewer')
    def test_evaluate_action_is_buy(self, MockBaseViewer, MockMarketStore):
        # Mocking the necessary objects
        mock_predictor = Mock()
        mock_predictor._stop = 1
        mock_predictor._limit = 1
        mock_predictor.predict.return_value = TradeAction.BUY
        mock_market = Mock()
        mock_market.get_pip_value.return_value = 1
        mock_market.pip_euro = 1
        mock_market_store = MockMarketStore.return_value
        mock_market_store.get_market.return_value = mock_market
        mock_viewer = MockBaseViewer.return_value

        # Creating a non-empty DataFrame
        df = DataFrame(
            {'date': [datetime(2024, 1, 1, 10), datetime(2024, 1, 1, 11)], 'open': [1.0, 1.0], 'close': [2.0, 2.0]})
        df_eval = DataFrame({'date': [datetime.now()], 'high': [1.0], 'low': [1.0], 'close': [1.0]})

        analytics = Analytics(mock_market_store,self._ig)
        result = analytics.evaluate(mock_predictor, df, df_eval, 'symbol', "epic" , 1, mock_viewer)

        self.assertIsInstance(result, EvalResult)
        self.assertEqual(result.get_trades(), 1)
        self.assertEqual(result.get_win_loss(), 0)
        self.assertEqual(result.get_average_reward(), 0)

    def test_simple_buy_and_sell(self):
        signals = pd.DataFrame({
            "index": [1, 5],
            "action": [TradeAction.BUY, TradeAction.SELL]
        })
        df_buy_results = {
            1: {
                "result": 5,
                "next_index": 3
            }
        }
        df_sell_results = {
            5: {
                "result": 10,
                "next_index": 15
            }
        }

        result = self._analytics.calculate_overall_result(signals, df_buy_results, df_sell_results, min_trades=0)
        self.assertEqual(result.wl, 100)
        self.assertEqual(result.reward, 15)

    def test_to_less_trades(self):
        signals = pd.DataFrame({
            "index": [1, 2],
            "action": [TradeAction.BUY, TradeAction.SELL]
        })
        df_buy_results = {
            1 : {
                "result": 5,
                "next_index":3
            }
        }
        df_sell_results = {
            2 : {
                "result": 5,
                "next_index": 3
            }
        }

        result = self._analytics.calculate_overall_result(signals, df_buy_results, df_sell_results)
        self.assertEqual(result.wl, 0)

