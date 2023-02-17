import unittest
from unittest.mock import MagicMock
from Logic.trader import Trader
from Tracing.ConsoleTracer import ConsoleTracer
from pandas import DataFrame,Series


class TraderTest(unittest.TestCase):


    def setUp(self):
        self._tracer = ConsoleTracer()
        pass

    def test_constructor(self):
        res = DataFrame()
        res = res.append(Series({"close":1,"high":2}),ignore_index=True)
        tiingo = MagicMock()
        tiingo.load_data_by_date = MagicMock(return_value=res)
        ig = MagicMock()
        #t = Trader("USD",ig,tiingo,self._tracer)