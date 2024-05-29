from BL.indicators import Indicators
from Predictors.base_predictor import BasePredictor
import unittest
from datetime import datetime
from pandas import DataFrame, Series

class TestBasePredictor(unittest.TestCase):


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
            ""
        ], index=["_type", "_stop", "_limit", "_active", "_symbol"])

        self.assertTrue(expected_series.equals(config_series))















