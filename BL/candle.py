from enum import Enum
from pandas import DataFrame


# https://www.myespresso.com/bootcamp/module/technical-analysis-basics/single-candlestick-patterns

# class syntax
class Direction(Enum):
    Bearish = 1
    Bullish = 2


class CandleType(Enum):
    Unknown = 0
    Doji = 1
    SpinningTop = 2
    WhiteMarubozu = 3
    BlackMarubozu = 4
    Hammer = 5
    HangingMan = 6
    ImvertedHammer = 7
    ShootingStar = 8
    DragonflyDoji = 9
    GraveStoneDoji = 10


class MultiCandleType(Enum):
    Unknown = 0
    EveningStar = 1
    MorningStart = 2
    ThreeBlackCrows = 3
    ThreeWhiteSoldiers = 4
    BullishEngulfing = 5
    BearishEngulfing = 6


class Candle:

    def __init__(self, ohlc):

        self.open = ohlc.open.item()
        self.close = ohlc.close.item()
        self.high = ohlc.high.item()
        self.low = ohlc.low.item()

    def direction(self) -> Direction:
        if self.open > self.close:
            return Direction.Bearish
        else:
            return Direction.Bullish

    def get_body_percentage(self):
        return self._calc_percentage(self.high - self.low, abs(self.open - self.close))

    @staticmethod
    def _calc_percentage(max, elemnt):
        if max == 0:
            return 0
        return 100 * elemnt / max

    def candle_type(self) -> CandleType:
        length = self.high - self.low
        body_length = abs(self.open - self.close)

        if self.direction() == Direction.Bullish:
            upper_shadow = self.high - self.close
            lower_shadow = self.open - self.low
        else:
            upper_shadow = self.high - self.open
            lower_shadow = self.close - self.low

        body_percentage = self._calc_percentage(length, body_length)
        upper_shadow_percentage = self._calc_percentage(length, upper_shadow)
        lower_shadow_percentage = self._calc_percentage(length, lower_shadow)

        # Doji
        if body_percentage < 5:
            if abs(upper_shadow_percentage - lower_shadow_percentage) < 15:
                return CandleType.Doji
            if upper_shadow_percentage < 5:
                return CandleType.DragonflyDoji
            if lower_shadow_percentage < 5:
                return CandleType.GraveStoneDoji

        if 5 <= body_percentage < 35:
            # Spinning top
            if abs(upper_shadow_percentage - lower_shadow_percentage) < 10:
                return CandleType.SpinningTop
            if (upper_shadow_percentage + body_percentage) < 38:
                # Hammer
                if self.direction() == Direction.Bullish:
                    return CandleType.Hammer
                else:
                    return CandleType.HangingMan
            elif (lower_shadow_percentage + body_percentage) < 38:
                if self.direction() == Direction.Bullish:
                    return CandleType.ImvertedHammer
                else:
                    return CandleType.ShootingStar

        if body_percentage > 80:
            if self.direction() == Direction.Bullish:
                return CandleType.WhiteMarubozu
            else:
                return CandleType.BlackMarubozu

        return CandleType.Unknown


class MultiCandle:

    def __init__(self, df: DataFrame):
        assert len(df) >= 3

        self.start = Candle(df[-3:-2])
        self.middle = Candle(df[-2:-1])
        self.end = Candle(df[-1:])

    # Trend Reversal

    def _is_evening_star(self):
        # https://smartmoney.angelone.in/chapter/5-most-important-multiple-candlestick-patterns-part-2/
        if self.start.direction() == Direction.Bullish and self.start.get_body_percentage() > 60:
            middle_type = self.middle.candle_type()
            if middle_type == CandleType.Doji or middle_type == CandleType.SpinningTop:
                if self.end.direction() == Direction.Bearish and self.end.get_body_percentage() > 60:
                    return True
        return False

    def _is_morning_star(self):
        # https://smartmoney.angelone.in/chapter/5-most-important-multiple-candlestick-patterns-part-2/
        if self.start.direction() == Direction.Bearish and self.start.get_body_percentage() > 60:
            middle_type = self.middle.candle_type()
            if middle_type == CandleType.Doji or middle_type == CandleType.SpinningTop:
                if self.end.direction() == Direction.Bullish and self.end.get_body_percentage() > 60:
                    return True
        return False

    @staticmethod
    def _is_black_crow(candle: Candle):
        return candle.direction() == Direction.Bearish and candle.get_body_percentage() > 60

    @staticmethod
    def _is_white_soldier(candle: Candle):
        return candle.direction() == Direction.Bullish and candle.get_body_percentage() > 60

    def _is_three_black_crows(self):
        # https://forexbee.co/three-black-crows/

        return self._is_black_crow(self.start) and \
            self._is_black_crow(self.middle) and \
            self._is_black_crow(self.end)

    def _is_three_white_soldiers(self):
        # https://forexbee.co/three-black-crows/

        return self._is_white_soldier(self.start) and \
            self._is_white_soldier(self.middle) and \
            self._is_white_soldier(self.end)

    def _is_bullish_engulfing(self):
        # https://forexbee.co/three-black-crows/

        if self.middle.direction() == Direction.Bearish and self.end.direction() == Direction.Bullish:
            if self.end.close > self.middle.open:
                return True

        return False

    def _is_bearish_engulfing(self):
        # https://forexbee.co/three-black-crows/

        if self.middle.direction() == Direction.Bullish and self.end.direction() == Direction.Bearish:
            if self.end.close < self.middle.open:
                return True

        return False

    #Continue



    def get_type(self) -> MultiCandleType:
        # https://forexbee.co/reversal-candlestick-patterns/
        if self._is_evening_star():
            return MultiCandleType.EveningStar
        if self._is_morning_star():
            return MultiCandleType.MorningStart
        if self._is_three_black_crows():
            return MultiCandleType.ThreeBlackCrows
        if self._is_three_white_soldiers():
            return MultiCandleType.ThreeWhiteSoldiers
        if self._is_bullish_engulfing():
            return MultiCandleType.BullishEngulfing
        if self._is_bearish_engulfing():
            return MultiCandleType.BearishEngulfing

        return MultiCandleType.Unknown

