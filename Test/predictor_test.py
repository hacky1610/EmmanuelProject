import unittest
from unittest.mock import MagicMock
from Predictors.cci_ema import CCI_EMA


class PredictorTest(unittest.TestCase):

    def test_set_config_default(self):
        pred = CCI_EMA({})
        pred.set_config("Foo")
        assert pred.upper_limit == 90

    def test_set_config_GBPUSD(self):
        pred = CCI_EMA({})
        pred.set_config("GBPUSD")
        assert pred.upper_limit == 90