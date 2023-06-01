import unittest
from unittest.mock import MagicMock
from BL.candle import Candle, Direction, CandleType
from pandas import Series


class CandleTest(unittest.TestCase):

    def setUp(self):
       pass

    def _create_ohlc(self,open,high,low,close):
        return Series([open,high,low,close], index=["open","high","low","close"])


    def test_direction(self):
        c = Candle(self._create_ohlc(90,100,80,101))
        assert c.direction() == Direction.Bullish

    def test_dragonfly(self):
        c = Candle(self._create_ohlc(90, 91, 50, 91))
        assert c.candle_type() == CandleType.DragonflyDoji

    def test_gravestone(self):
        c = Candle(self._create_ohlc(90, 200, 90, 91))
        assert c.candle_type() == CandleType.GraveStoneDoji


