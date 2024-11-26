from unittest.mock import MagicMock

import numpy as np
import pandas
import pandas as pd

from BL.datatypes import TradeAction
from BL.indicators import Indicators
from Predictors.base_predictor import BasePredictor
import unittest
from datetime import datetime
from pandas import DataFrame, Series

from Predictors.deep_predictor import DeepPredictor


class TestBasePredictor(unittest.TestCase):

    def setUp(self):
        self._df = DataFrame()
        self._df = self.add_line(self._df, "2023-01-01T13:00:00.00Z", 900, 950, 850, 900)
        self._df = self.add_line(self._df, "2023-01-01T14:00:00.00Z", 900, 950, 850, 900)
        self._df = self.add_line(self._df, "2023-01-01T15:00:00.00Z", 900, 950, 850, 900)
        self._df = self.add_line(self._df, "2023-01-01T16:00:00.00Z", 900, 950, 850, 900, action=TradeAction.SELL)
        self._df = self.add_line(self._df, "2023-01-01T17:00:00.00Z", 900, 950, 850, 900)
        self._df = self.add_line(self._df, "2023-01-01T18:00:00.00Z", 900, 950, 850, 900)
        self._df = self.add_line(self._df, "2023-01-01T19:00:00.00Z", 900, 950, 850, 900)
        self._df = self.add_line(self._df, "2023-01-01T20:00:00.00Z", 900, 950, 850, 900)

    def test_setup(self):
        config = {
            "_limit": 1.5,
            "_stop": 1.5,
            "_scan_time": datetime(2023, 7, 31, 18, 0, 0),
            "_reward": 100.0,
            "_trades": 10,
            "_wins": 7,
            "_len_df": 1000,
            "_trade_minutes": 240
        }
        base_predictor = BasePredictor(symbol="", indicators=Indicators(), config=config)

        self.assertEqual(base_predictor._limit, 1.5)
        self.assertEqual(base_predictor._stop, 1.5)
        self.assertEqual(base_predictor.get_last_scan_time(), datetime(2023, 7, 31, 18, 0, 0))



    def add_line(self, df: DataFrame, date, open, high, low, close, action=TradeAction.NONE):
        new_row = pd.DataFrame({
            "open": [open],
            "high": [high],
            "low": [low],
            "close": [close],
            "date": [date],
            "action": [action]
        })
        # Kombiniere den ursprünglichen DataFrame mit der neuen Zeile
        return pd.concat([df, new_row], ignore_index=True)

    def test_predict_not_implemented(self):
        base_predictor = BasePredictor("",Indicators())

        with self.assertRaises(NotImplementedError):
            base_predictor.predict(DataFrame())

    def test_get_config(self):
        base_predictor = BasePredictor("",Indicators())
        base_predictor._limit = 1.5
        base_predictor._stop = 1.5

        config_series = base_predictor.get_config()

        expected_series = Series([
            "BasePredictor",
            1.5,
            1.5,
            True,
            "",
            False,
            False,
            0.7,
            6.0,
            14.0
        ], index=["_type", "_stop", "_limit", "_active", "_symbol", "_use_isl", "_isl_open_end", "_isl_factor", "_isl_distance", "_isl_entry"])

        self.assertTrue(expected_series.equals(config_series))

    def test_save_load_features(self):
        dp = DeepPredictor("", MagicMock(), Indicators())
        feature_factors = pandas.Series([1.0,0.1], index=["A", "B"])
        dp.set_buy_validation(0.8,4,0.5,feature_factors)

        c = dp.get_config().to_dict()

        dp1 = DeepPredictor("", MagicMock(), Indicators())
        dp1.setup(c)
        print(dp1._buy_features)




    def test_predict_buy(self):


        indicators = MagicMock()
        indicators.predict_single.return_value = "both"

        buy_model = MagicMock()
        mocked_probabilities = np.array([[0.3, 0.7], [0.4, 0.6], [0.2, 0.8]])
        buy_model.predict_proba.return_value = mocked_probabilities

        dp = DeepPredictor("", MagicMock(),  indicators)
        feature_factors = pandas.Series([1.0, 0.1], index=["A", "B"])
        dp.set_model_buy(buy_model)
        dp.set_buy_validation(0.8, 4, 0.5, feature_factors)

        res = dp.predict( self._df)
        assert res == TradeAction.BUY

    def test_predict_no_buy(self):
        indicators = MagicMock()
        indicators.predict_single.return_value = "both"

        buy_model = MagicMock()
        mocked_probabilities = np.array([[0.3, 0.7], [0.4, 0.6], [0.2, 0.8]])
        buy_model.predict_proba.return_value = mocked_probabilities

        dp = DeepPredictor("", MagicMock(), indicators)
        feature_factors = pandas.Series([1.0, 0.1], index=["A", "B"])
        dp.set_model_buy(buy_model)
        dp.set_buy_validation(0.8, 4, 0.9, feature_factors)

        res = dp.predict(self._df)
        assert res == TradeAction.NONE

    def test_predict_sell(self):
        indicators = MagicMock()
        indicators.predict_single.return_value = "both"

        sell_model = MagicMock()
        mocked_probabilities = np.array([[0.3, 0.7], [0.4, 0.6], [0.2, 0.8]])
        sell_model.predict_proba.return_value = mocked_probabilities

        dp = DeepPredictor("", MagicMock(), indicators)
        feature_factors = pandas.Series([1.0, 0.1], index=["A", "B"])
        dp.set_model_sell(sell_model)
        dp.set_sell_validation(0.8, 4, 0.5, feature_factors)

        res = dp.predict(self._df)
        assert res == TradeAction.SELL

    def test_predict_no_sell(self):
        indicators = MagicMock()
        indicators.predict_single.return_value = "both"

        sell_model = MagicMock()
        mocked_probabilities = np.array([[0.3, 0.7], [0.4, 0.6], [0.2, 0.8]])
        sell_model.predict_proba.return_value = mocked_probabilities

        dp = DeepPredictor("", MagicMock(), indicators)
        feature_factors = pandas.Series([1.0, 0.1], index=["A", "B"])
        dp.set_model_sell(sell_model)
        dp.set_sell_validation(0.8, 4, 0.9, feature_factors)

        res = dp.predict(self._df)
        assert res == TradeAction.NONE















