from enum import Enum

from BL.high_low_scanner import HighLowScanner


class PatternType(Enum):
    Unknown = 0
    DoubleTop = 1


class ChartPattern:

    def __init__(self, hl_scanner:HighLowScanner):
        self._hl_scanner = hl_scanner

    def _is_double_top(self):
        hl = self._hl_scanner.get_high_low()
        if len(hl) >= 3:
            return hl[-1:][self._hl_scanner.COLUMN_NAME].item() == self._hl_scanner.MAX and \
                hl[-2:-1][self._hl_scanner.COLUMN_NAME].item() == self._hl_scanner.MIN and \
                    hl[-3:-2][self._hl_scanner.COLUMN_NAME].item() == self._hl_scanner.MAX


        return False

    def get_pattern(self, prices) -> PatternType:

        self._hl_scanner.scan(prices, 5)
        if self._is_double_top():
            return PatternType.DoubleTop

        return PatternType.Unknown
