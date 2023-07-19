import unittest
from pandas import Series, DataFrame

from Predictors.base_predictor import BasePredictor


class PredictorTest(unittest.TestCase):

    def test_set_config_default(self):
        pred = BasePredictor()
        pred.load("Foo")
        assert pred.version == "V1.0"







