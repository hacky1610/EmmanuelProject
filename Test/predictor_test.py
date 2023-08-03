from Predictors.base_predictor import BasePredictor
import unittest
from datetime import datetime
from pandas import DataFrame, Series

from Predictors.chart_pattern import ChartPatternPredictor


class TestBasePredictor(unittest.TestCase):

    def test_get_last_scan_time(self):
        base_predictor = BasePredictor()
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
        base_predictor = BasePredictor(config)

        self.assertEqual(base_predictor.limit, 1.5)
        self.assertEqual(base_predictor.stop, 1.5)
        self.assertEqual(base_predictor.version, "V2.0")
        self.assertEqual(base_predictor.get_last_scan_time(), datetime(2023, 7, 31, 18, 0, 0))


    def test_predict_not_implemented(self):
        base_predictor = BasePredictor()

        with self.assertRaises(NotImplementedError):
            base_predictor.predict(DataFrame())

    def test_get_config(self):
        base_predictor = BasePredictor()
        base_predictor.limit = 1.5
        base_predictor.stop = 1.5
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


class TestChartPatternPredictor(unittest.TestCase):

    def setUp(self):
        self.config = {
            "_limit_factor": 2.5,
            "_look_back": 30,
            "_be4after": 4,
            "_max_dist_factor": 1.8,
            "_local_look_back": 2,
            "stop": 2.0,
            "limit": 2.0,
            "version": "V1.0",
            "last_scan": datetime(2023, 7, 31, 18, 0, 0).isoformat(),
            "_reward": 100.0,
            "_trades": 10,
            "_wins": 7,
            "_len_df": 1000,
            "_trade_minutes": 240
        }

        self.bull_df = DataFrame({
            'EMA_20': [50.0, 55.0, 60.0],
            'EMA_50': [40.0, 45.0, 50.0],
            'ATR': [2.5, 2.0, 1.5]
        })

        self.bear_df = DataFrame({
            'EMA_20': [20.0, 30.0, 30.0],
            'EMA_50': [40.0, 45.0, 50.0],
            'ATR': [2.5, 2.0, 1.5]
        })

        # Hier können Sie die Eigenschaften der Instanz (self._limit_factor usw.) setzen,
        # die für Ihre spezifischen Testfälle relevant sind.
        # Beispiel:
        self._predictor = ChartPatternPredictor(self.config)
        self._predictor._limit_factor = 1.5

    def test_setup(self):
        predictor = ChartPatternPredictor(self.config)

        self.assertEqual(predictor._limit_factor, 2.5)
        self.assertEqual(predictor._look_back, 30)
        self.assertEqual(predictor._be4after, 4)
        self.assertEqual(predictor._max_dist_factor, 1.8)
        self.assertEqual(predictor._local_look_back, 2)



    def test_buy_with_uptrend(self):
        # Testen, ob die Funktion "BUY" mit einem Aufwärtstrend zurückgibt.
        action, stop, limit = self._predictor.is_with_trend(BasePredictor.BUY, self.bull_df)
        self.assertEqual(action, BasePredictor.BUY)
        self.assertEqual(stop, self.bull_df.ATR.mean() * self._predictor._limit_factor)
        self.assertEqual(limit, self.bull_df.ATR.mean() * self._predictor._limit_factor)

    def test_sell_with_downtrend(self):
        # Testen, ob die Funktion "SELL" mit einem Abwärtstrend zurückgibt.
        action, stop, limit = self._predictor.is_with_trend(BasePredictor.SELL, self.bear_df)
        self.assertEqual(action,  BasePredictor.SELL)
        self.assertEqual(stop, self.bull_df.ATR.mean() * self._predictor._limit_factor)
        self.assertEqual(limit, self.bull_df.ATR.mean() * self._predictor._limit_factor)

    def test_no_action_against_trend(self):
        # Testen, ob die Funktion "NONE" zurückgibt, wenn die Aktion gegen den Trend ist.
        action, stop, limit = self._predictor.is_with_trend(BasePredictor.SELL,
                                                            self.bull_df)  # Nehmen Sie eine ungültige Aktion, um gegen den Trend zu gehen.
        self.assertEqual(action, BasePredictor.NONE)
        self.assertEqual(stop, 0)
        self.assertEqual(limit, 0)

        action, stop, limit = self._predictor.is_with_trend(BasePredictor.BUY,
                                                            self.bear_df)  # Nehmen Sie eine ungültige Aktion, um gegen den Trend zu gehen.
        self.assertEqual(action, BasePredictor.NONE)
        self.assertEqual(stop, 0)
        self.assertEqual(limit, 0)
    def test_get_config(self):
        predictor = ChartPatternPredictor(self.config)

        config_series = predictor.get_config()

        expected_series = Series([
            ChartPatternPredictor.__class__.__name__,
            2.0,
            2.0,
            "V1.0",
            datetime(2023, 7, 31, 18, 0, 0).isoformat(),
            2.5,
            30,
            4,
            1.8,
            2
        ], index=[
            "Type",
            "stop",
            "limit",
            "version",
            "last_scan",
            "_limit_factor",
            "_look_back",
            "_be4after",
            "_max_dist_factor",
            "_local_look_back"
        ])

        self.assertTrue(expected_series.equals(config_series))













