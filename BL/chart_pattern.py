from enum import Enum

from pandas import DataFrame

from BL.high_low_scanner import HighLowScanner,HlType,Item
from Predictors.base_predictor import BasePredictor
from UI.base_viewer import BaseViewer


class PatternType(Enum):
    Unknown = 0
    DoubleTop = 1
    Triangle = 2


class ChartPattern:

    def __init__(self, hl_scanner, prices: DataFrame,viewer:BaseViewer=BaseViewer()):
        self._hl_scanner = hl_scanner
        self._prices = prices
        self._level_diff = prices.ATR.mean() * 0.7
        self._max_dist_to_min = prices.ATR.mean() * 2
        self._viewer = viewer
        self._min_diff_of_points = 2

    def calc_cross_point(self, xa, xb, ya, yb, xz):
        diff_id_a_b = xb - xa
        diff_vall_a_b = yb - ya

        factor = diff_vall_a_b / diff_id_a_b

        diff_id_b_z = xz - xb

        return diff_id_b_z * factor + yb



    def _is_same_level(self, a, b):
        return abs(a - b) < self._level_diff

    def _is_double_top(self):
        hl = self._hl_scanner.get_high_low_items()

        def correct_form():
            return hl[-1].type ==  HlType.HIGH and \
                hl[-2].type == HlType.LOW and \
                hl[-3].type == HlType.HIGH

        def same_high():
            return self._is_same_level(hl[-1].value, hl[-3].value)

        def second_high_lower():
            return hl[-1].value < hl[-3].value

        def close_under_min():
            current_close = self._prices[-1:].close.item()
            current_open = self._prices[-1:].open.item()
            return current_close < hl[-2].value < current_open


        if len(hl) >= 3:
            return correct_form() and same_high() and close_under_min() and second_high_lower()

        return False

    def _is_triangle(self):
        from ta import trend



        return False, BasePredictor.NONE

    def get_pattern(self) -> str:

        self._hl_scanner.scan(self._prices, 6)
        is_triangel, action = self._is_triangle()
        if is_triangel:
            return action

        return BasePredictor.NONE

