import unittest
from unittest.mock import MagicMock
from Logic.trader import Trader
from Tracing.ConsoleTracer import ConsoleTracer
from pandas import DataFrame,Series
from Data.data_processor import DataProcessor
from Logic.trainer import Trainer


class TraderTest(unittest.TestCase):


    def setUp(self):
        self._tracer = ConsoleTracer()
        self._dataProcessor = DataProcessor()
        pass

    def test_trade_no_datafrom_tiingo(self):
        res = DataFrame()
        tiingo = MagicMock()
        tiingo.load_data_by_date = MagicMock(return_value=res)
        ig = MagicMock()
        trainer = MagicMock()
        t = Trader("USD",ig,tiingo,self._tracer,trainer,self._dataProcessor)
        res = t.trade()
        assert res == False

    def test_trade_has_open_positions(self):
        res = DataFrame()
        res = res.append(Series({
            "close":23, "SMA7":3, "EMA":4, "BB_UPPER":5, "BB_MIDDLE":6, "BB_LOWER":6, "ROC":7, "%R":8, "MACD":4,
             "SIGNAL":6}
        ),ignore_index=True)
        tiingo = MagicMock()
        tiingo.load_data_by_date = MagicMock(return_value=res)
        ig = MagicMock()
        ig.has_opened_positions = MagicMock(return_value=True)
        trainer = MagicMock()
        t = Trader("USD", ig, tiingo, self._tracer, trainer, self._dataProcessor)
        res = t.trade()
