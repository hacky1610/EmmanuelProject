from BL.indicators import Indicators
from Predictors.base_predictor import BasePredictor
import unittest
from datetime import datetime
from pandas import DataFrame, Series

from Predictors.chart_pattern import ChartPatternPredictor


class TestBasePredictor(unittest.TestCase):

    def test_get_last_scan_time(self):
        base_predictor = BasePredictor(Indicators())
        base_predictor.last_scan = datetime(2023, 8, 1, 12, 0, 0).isoformat()

        last_scan_time = base_predictor.get_last_scan_time()

        self.assertEqual(last_scan_time, datetime(2023, 8, 1, 12, 0, 0))

    def test_setup(self):
        config = {
            "limit": 1.5,
            "stop": 1.5,
            "version": "V2.0",
            "last_scan": datetime(2023, 7, 31, 18, 0, 0).isoformat(),
            "_reward": 100.0,
            "_trades": 10,
            "_wins": 7,
            "_len_df": 1000,
            "_trade_minutes": 240
        }
        base_predictor = BasePredictor(indicators=Indicators(), config=config)

        self.assertEqual(base_predictor._limit, 1.5)
        self.assertEqual(base_predictor._stop, 1.5)
        self.assertEqual(base_predictor.version, "V2.0")
        self.assertEqual(base_predictor.get_last_scan_time(), datetime(2023, 7, 31, 18, 0, 0))


    def test_predict_not_implemented(self):
        base_predictor = BasePredictor(Indicators())

        with self.assertRaises(NotImplementedError):
            base_predictor.predict(DataFrame())

    def test_get_config(self):
        base_predictor = BasePredictor(Indicators())
        base_predictor._limit = 1.5
        base_predictor._stop = 1.5
        base_predictor.version = "V2.0"
        base_predictor.last_scan = datetime(2023, 7, 31, 18, 0, 0).isoformat()

        config_series = base_predictor.get_config()

        expected_series = Series([
            "BasePredictor",
            1.5,
            1.5,
            "V2.0",
            datetime(2023, 7, 31, 18, 0, 0).isoformat()
        ], index=["Type", "stop", "limit", "version", "last_scan"])

        self.assertTrue(expected_series.equals(config_series))















