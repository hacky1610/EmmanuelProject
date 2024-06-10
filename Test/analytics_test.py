import unittest
from unittest.mock import Mock, patch
from pandas import DataFrame
from BL.analytics import Analytics
from BL.datatypes import TradeAction
from BL.eval_result import EvalResult
from datetime import datetime

class TestAnalytics(unittest.TestCase):


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

        analytics = Analytics(mock_market_store)
        result = analytics.evaluate(mock_predictor, df, df_eval, 'symbol', 1, mock_viewer)

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
        df_eval = DataFrame({'date': [datetime.now()], 'high': [1.0], 'low': [1.0]})

        analytics = Analytics(mock_market_store)
        result = analytics.evaluate(mock_predictor, df, df_eval, 'symbol', 1, mock_viewer)

        self.assertIsInstance(result, EvalResult)
        self.assertEqual(result.get_trades(), 0)
        self.assertEqual(result.get_win_loss(), 0)
        self.assertEqual(result.get_average_reward(), 0)

