from enum import Enum

import numpy as np
import pandas as pd
from scipy.signal import argrelextrema, find_peaks


class PatternType(Enum):
    Unknown = 0
    DoubleTop = 1


class ChartPattern:
    _smoothing = 5
    _window_range = 5
    _look_back = 50
    MAX = "max"
    MIN = "min"

    def get_max_min(self, prices):
        prices = prices[self._look_back * -1:]
        #smooth_prices = prices['close'].rolling(window=self._smoothing).mean().dropna()
        local_max = argrelextrema(prices.values, np.greater, order=10)[0]
        local_min = argrelextrema(prices.values, np.less, order=10)[0]
        price_local_max_dt = []
        for i in local_max:
            if (i > self._window_range) and (i < len(prices) - self._window_range):
                price_local_max_dt.append(prices.iloc[i - self._window_range:i + self._window_range]['close'].idxmax())
        price_local_min_dt = []
        for i in local_min:
            if (i > self._window_range) and (i < len(prices) - self._window_range):
                price_local_min_dt.append(prices.iloc[i - self._window_range:i + self._window_range]['close'].idxmin())
        maxima = pd.DataFrame(prices.loc[price_local_max_dt])
        maxima["type"] = self.MAX
        minima = pd.DataFrame(prices.loc[price_local_min_dt])
        minima["type"] = self.MIN
        max_min = pd.concat([maxima, minima]).sort_index()
        max_min.set_index('date')
        max_min = max_min.reset_index()
        max_min = max_min[~max_min.date.duplicated()]
        return max_min.filter(["date", "close","type"])

    def get_max_minV2(self, prices):
        smooth_prices = prices['close'].rolling(window=self._smoothing).mean().dropna()
        peaks= find_peaks(prices.close, threshold=prices.ATR.mean() * .3)
        prices.loc[peaks[0].tolist(), "type"] = "peak"
        return prices

    def get_max_minV3(self, prices):
        smooth_prices = prices['close'].rolling(window=self._smoothing).mean().dropna()
        peaks = indexes(prices.close,thres=0.7)
        prices.loc[peaks, "type"] = "peak"
        return prices


    def _is_double_top(self, min_max):
        if len(min_max) >= 2:
            period = min_max[-2:]
            return len(period[period.type == self.MAX]) == 2

        return False

    def get_pattern(self, prices) -> PatternType:

        min_max = self.get_max_min(prices)

        if self._is_double_top(min_max):
            return PatternType.DoubleTop

        return PatternType.Unknown
