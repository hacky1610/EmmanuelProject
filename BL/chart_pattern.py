from enum import Enum

from pandas import DataFrame

from BL.high_low_scanner import HighLowScanner


class PatternType(Enum):
    Unknown = 0
    DoubleTop = 1
    Triangle = 1


class ChartPattern:

    def __init__(self, hl_scanner: HighLowScanner, prices: DataFrame):
        self._hl_scanner = hl_scanner
        self._prices = prices
        self._level_diff = prices.ATR.mean() * 0.7
        self._max_dist_to_min = prices.ATR.mean() * 2

    def _is_same_level(self, a, b):
        return abs(a - b) < self._level_diff

    def _is_double_top(self):
        hl = self._hl_scanner.get_high_low()

        def correct_form():
            return hl[-1:][self._hl_scanner.COLUMN_NAME].item() == self._hl_scanner.MAX and \
                hl[-2:-1][self._hl_scanner.COLUMN_NAME].item() == self._hl_scanner.MIN and \
                hl[-3:-2][self._hl_scanner.COLUMN_NAME].item() == self._hl_scanner.MAX

        def same_high():
            return self._is_same_level(hl[-1:].high.item(), hl[-3:-2].high.item())

        def second_high_lower():
            return hl[-1:].high.item() < hl[-3:-2].high.item()

        def close_under_min():
            current_close = self._prices[-1:].close.item()
            current_open = self._prices[-1:].open.item()
            return current_close < hl[-2:-1].low.item() < current_open


        if len(hl) >= 3:
            return correct_form() and same_high() and close_under_min() and second_high_lower()

        return False

    def _is_triangle(self):
        hl = self._hl_scanner.get_high_low()

        def correct_form():
            if hl[-1:][self._hl_scanner.COLUMN_NAME].item() == self._hl_scanner.MAX:
                h1 = hl[-1:].high.item()
                h2 = hl[-3:-2].high.item()
                l1 = hl[-2:-1].low.item()
                l2 = hl[-4:-3].low.item()

                return h1 < h2 and l1 > l2

        if len(hl) >= 4:
            return correct_form()

        return False

    def get_pattern(self) -> PatternType:

        self._hl_scanner.scan(self._prices, 5)
        if self._is_double_top():
            return PatternType.DoubleTop
        if self._is_triangle():
            return PatternType.DoubleTop

        return PatternType.Unknown
