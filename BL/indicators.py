from typing import List

import pandas as pd
from pandas import DataFrame

from BL import DataProcessor
from BL.candle import Candle, Direction, MultiCandle, MultiCandleType
from BL.datatypes import TradeAction
import random

from BL.high_low_scanner import PivotScanner
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.Tracer import Tracer


class Indicator:
    def __init__(self, name, function):
        self.name = name
        self.function = function


class Indicators:
    # region Static Members
    # region RSI
    RSI = "rsi"
    RSI_LIMIT = "rsi_limit"
    RSI_LIMIT_4H = "rsi_limit_4h"
    RSI_BREAK = "rsi_break"
    RSI_BREAK_4H = "rsi_break_4h"
    RSI_BREAK3070 = "rsi_break_30_70"
    RSI30_70 = "rsi_30_70"
    RSISLOPE = "rsi_slope"
    RSI_CONVERGENCE = "rsi_convergence"
    RSI_CONVERGENCE5 = "rsi_convergence5"
    RSI_CONVERGENCE5_30 = "rsi_convergence5_30"
    RSI_CONVERGENCE5_40 = "rsi_convergence5_40"
    RSI_CONVERGENCE7 = "rsi_convergence7"
    # endregion
    # region Williams
    WILLIAMS_LIMIT = "williams_limit"
    WILLIAMS_BREAK = "williams_break"
    # endregion
    # region TII
    TII_50 = "tii_50"
    TII_20_80 = "tii_20_80"
    # endregion
    # MACD
    MACD = "macd"
    MACD_ZERO = "macd_zero"
    MACDCROSSING = "macd_crossing"
    MACDSINGALDIFF = "macd_signal_diff"
    MACD_CONVERGENCE = "macd_convergence"
    MACD_MAX = "macd_max"
    MACD_MAX_4H = "macd_max_4h"
    MACD_SLOPE = "macd_slope"
    # EMA
    EMA = "ema"
    EMA_HIST = "ema_hist"
    EMA_ALLIGATOR = "ema_alligator"
    EMA_ALLIGATOR_HIST = "ema_alligator_hist"
    EMA10_50 = "ema_10_50"
    EMA20_CLOSE = "ema_20_close"
    SMMA20_CLOSE = "smma_20_close"
    EMA20_SMMA20 = "ema_20_smma_20"
    EMA_20_CHANNEL = "ema_20_channel"

    # Others
    ADX = "adx"
    ADX_SLOPE = "adx_slope"
    ADX_SLOPE_21 = "adx_slope_21"
    ADX_SLOPE_48 = "adx_slope_48"
    ADX_BREAK = "adx_break"
    ADX_MAX = "adx_max"
    ADX_MAX_4H = "adx_max_4h"
    ADX_MAX2 = "adx_max2"
    ADX_MAX_21 = "adx_max_21"
    ADX_MAX_48 = "adx_max_48"
    PSAR = "psar"
    PSAR_CHANGE = "psar_change"
    CCI = "cci"
    CANDLE = "candle"
    CANDLEPATTERN = "candle_pattern"
    # Bollinger
    BB = "bb"
    BB_MIDDLE_CROSS = "bb_middle_crossing"
    BB_BORDER_CROSS = "bb_border_crossing"
    # ICHIMOKU
    ICHIMOKU = "ichi"
    ICHIMOKU_KIJUN_CONFIRM = "ichi_kijun_confirm"
    ICHIMOKU_KIJUN_CONFIRM_4H = "ichi_kijun_confirm_4h"
    ICHIMOKU_KIJUN_CROSS_CONFIRM = "ichi_kijun_cross_confirm"
    ICHIMOKU_CLOUD_CONFIRM = "ichi_cloud_confirm"
    ICHIMOKU_CLOUD_THICKNESS = "ichi_cloud_thickness"

    # endregion

    # region Constructor
    def __init__(self, tracer: Tracer = ConsoleTracer()):
        self._indicators = []
        self._indicator_confirm_factor = 0.7
        # RSI
        self._add_indicator(self.RSI, self._rsi_predict)
        self._add_indicator(self.RSI_LIMIT, self._rsi_limit_predict)
        self._add_indicator(self.RSI_LIMIT_4H, self._rsi_limit_predict_4h)
        self._add_indicator(self.RSI_BREAK, self._rsi_break_predict)
        self._add_indicator(self.RSI_BREAK3070, self._rsi_break_30_70_predict)
        self._add_indicator(self.RSI_CONVERGENCE, self._rsi_convergence_predict3)
        self._add_indicator(self.RSI_CONVERGENCE5, self._rsi_convergence_predict5)
        self._add_indicator(self.RSI_CONVERGENCE5_30, self._rsi_convergence_predict5_30)
        self._add_indicator(self.RSI_CONVERGENCE5_40, self._rsi_convergence_predict5_40)
        self._add_indicator(self.RSI_CONVERGENCE7, self._rsi_convergence_predict7)
        self._add_indicator(self.RSI30_70, self._rsi_smooth_30_70_predict)
        self._add_indicator(self.RSISLOPE, self._rsi_smooth_slope_predict)
        self._add_indicator(self.RSI_BREAK_4H, self._rsi_break_predict_4h)

        self._add_indicator(self.TII_50, self._tii_50)
        self._add_indicator(self.TII_20_80, self._tii_20_80)

        # Williams
        self._add_indicator(self.WILLIAMS_BREAK, self._williams_break_predict)
        self._add_indicator(self.WILLIAMS_LIMIT, self._williams_limit_predict)

        # MACD
        self._add_indicator(self.MACD, self._macd_predict)
        self._add_indicator(self.MACD_SLOPE, self._macd_slope_predict)
        self._add_indicator(self.MACD_MAX, self._macd_max_predict)
        self._add_indicator(self.MACD_MAX_4H, self._macd_max_predict_4h)
        self._add_indicator(self.MACD_ZERO, self._macd_predict_zero_line)
        self._add_indicator(self.MACDCROSSING, self._macd_crossing_predict)
        self._add_indicator(self.MACD_CONVERGENCE, self._macd_convergence_predict)
        self._add_indicator(self.MACDSINGALDIFF, self._macd_signal_diff_predict)

        # EMA
        self._add_indicator(self.EMA, self._ema_predict)
        self._add_indicator(self.EMA_ALLIGATOR, self._ema_alligator_predict)
        self._add_indicator(self.EMA_HIST, self._ema_hist_predict)
        self._add_indicator(self.EMA_ALLIGATOR_HIST, self._ema_alligator_hist_predict)
        self._add_indicator(self.EMA10_50, self._ema_10_50_diff)
        self._add_indicator(self.EMA20_CLOSE, self._ema_20_close)
        self._add_indicator(self.SMMA20_CLOSE, self._smma_20_close)
        self._add_indicator(self.EMA20_SMMA20, self._ema_20_smma_20)
        self._add_indicator(self.EMA_20_CHANNEL, self._ema_20_channel)

        # ADX
        self._add_indicator(self.ADX, self._adx_predict)
        self._add_indicator(self.ADX_SLOPE, self._adx_slope_predict)
        self._add_indicator(self.ADX_SLOPE_21, self._adx_slope_predict_21)
        self._add_indicator(self.ADX_SLOPE_48, self._adx_slope_predict_48)
        self._add_indicator(self.ADX_MAX, self._adx_max_predict)
        self._add_indicator(self.ADX_MAX_4H, self._adx_max_predict_4h)
        self._add_indicator(self.ADX_MAX_21, self._adx_max_predict_21)
        self._add_indicator(self.ADX_MAX_48, self._adx_max_predict_48)
        self._add_indicator(self.ADX_MAX2, self._adx_max_predict2)
        self._add_indicator(self.ADX_BREAK, self._adx__break_predict)

        # Others

        self._add_indicator(self.CANDLE, self._candle_predict)
        self._add_indicator(self.CANDLEPATTERN, self._candle_pattern_predict)
        self._add_indicator(self.CCI, self._cci_predict)

        # PSAR
        self._add_indicator(self.PSAR, self._psar_predict)
        self._add_indicator(self.PSAR_CHANGE, self._psar_change_predict)

        # Bollinger
        self._add_indicator(self.BB, self._bb_predict)
        self._add_indicator(self.BB_MIDDLE_CROSS, self._bb_middle_cross_predict)
        self._add_indicator(self.BB_BORDER_CROSS, self._bb_border_cross_predict)

        # ICHIMOKU
        self._add_indicator(self.ICHIMOKU, self._ichimoku_predict)
        self._add_indicator(self.ICHIMOKU_KIJUN_CONFIRM, self._ichimoku_kijun_close_predict)
        self._add_indicator(self.ICHIMOKU_KIJUN_CONFIRM_4H, self._ichimoku_kijun_close_predict_4h)
        self._add_indicator(self.ICHIMOKU_KIJUN_CROSS_CONFIRM, self._ichimoku_kijun_close_cross_predict)
        self._add_indicator(self.ICHIMOKU_CLOUD_CONFIRM, self._ichimoku_cloud_thickness_predict)
        self._add_indicator(self.ICHIMOKU_CLOUD_THICKNESS, self._ichimoku_cloud_thickness_predict)

        self._tracer: Tracer = tracer

    # endregion

    def convert_1h_to_4h(self, one_h_df: DataFrame):
        if len(one_h_df) == 0:
            return DataFrame()

        one_h_df['date_index'] = pd.to_datetime(one_h_df['date'])
        # Gruppieren nach 4 Stunden und Aggregation der Kursdaten
        df_4h: DataFrame = one_h_df.groupby(pd.Grouper(key='date_index', freq='4H')).agg({
            'open': 'first',  # Erster Kurs in der 4-Stunden-Periode
            'high': 'max',  # Höchster Kurs in der 4-Stunden-Periode
            'low': 'max',  # Höchster Kurs in der 4-Stunden-Periode
            'close': 'last',  # Höchster Kurs in der 4-Stunden-Periode
            'date_index': 'first'  # Erstes Zeitstempel in der 4-Stunden-Periode
        }).reset_index(drop=True)
        df_4h.dropna(inplace=True)
        df_4h.reset_index(inplace=True)

        df_4h = df_4h.filter(["open", "low", "high", "close"])
        dp = DataProcessor()
        dp.addSignals_big_tf(df_4h)

        return df_4h.dropna()

    # region Get/Add Indicators
    def _add_indicator(self, name, function):
        self._indicators.append(Indicator(name, function))

    def _get_indicator_by_name(self, name):
        for i in self._indicators:
            if i.name == name:
                return i

        return None

    def get_all_indicator_names(self, skip: List = None):
        all_indicator_names = [indikator.name for indikator in self._indicators]

        if skip is not None:
            all_indicator_names = [element for element in all_indicator_names if element not in skip]

        return all_indicator_names

    def get_random_indicator_names(self, must: str = None, skip: List = None, min: int = 3, max: int = 6):
        all_indicator_names = self.get_all_indicator_names(skip)

        r = random.choices(all_indicator_names, k=random.randint(min, max))
        if must is not None:
            r.append(must)

        return list(set(r))

    def _get_indicators_by_names(self, names):
        indicators = []
        for n in names:
            i = self._get_indicator_by_name(n)
            if i is not None:
                indicators.append(i)

        return indicators

    # endregion

    # region Predict
    def _predict(self, predict_values, max_none=0):

        self._tracer.debug(f"Predict for multiple values {predict_values} and max_none {max_none}")
        nones = predict_values.count(TradeAction.NONE)
        if nones > max_none:
            return TradeAction.NONE

        if (predict_values.count(TradeAction.BUY) + predict_values.count(TradeAction.BOTH) + predict_values.count(
                TradeAction.NONE)) >= len(
                predict_values):
            return TradeAction.BUY
        elif (predict_values.count(TradeAction.SELL) + predict_values.count(TradeAction.BOTH) + predict_values.count(
                TradeAction.NONE)) >= len(
                predict_values):
            return TradeAction.SELL

        return TradeAction.NONE

    def predict_some(self, df, indicator_names, max_none=0):
        predict_values = []
        for indicator in self._get_indicators_by_names(indicator_names):
            predict_values.append(indicator.function(df))

        return self._predict(predict_values, max_none)

    def predict_all(self, df, factor: float = 0.7, exclude: list = []):
        predict_values = []
        for indicator in self._indicators:
            if indicator.name not in exclude:
                predict_values.append(indicator.function(df))

        return self._predict(predict_values, factor)

    # endregion

    # region BL
    def _ema_predict(self, df):
        current_ema_10 = df.EMA_10.iloc[-1]
        current_ema_20 = df.EMA_20.iloc[-1]
        current_ema_30 = df.EMA_30.iloc[-1]

        if current_ema_10 > current_ema_20 > current_ema_30:
            return TradeAction.BUY
        elif current_ema_30 > current_ema_20 > current_ema_10:
            return TradeAction.SELL

        return TradeAction.NONE

    def _rsi_break_predict_4h(self, df):
        try:
            df4h = self.convert_1h_to_4h(df)
            return self._oscillator_break(df4h, "RSI", 50, 50)
        except Exception as e:
            print(f"Error during indication {e}.")
            print(f"1h {df}.")
            print(f"4h {df4h}.")

        return TradeAction.NONE

    def _ema_hist_predict(self, df):
        if len(df) < 4:
            return TradeAction.NONE

        period = df[-3:]

        if len(period[period.EMA_10 > period.EMA_20]) > 0 and len(period[period.EMA_20 > period.EMA_30]) > 0:
            return TradeAction.BUY
        elif len(period[period.EMA_10 < period.EMA_20]) > 0 and len(period[period.EMA_20 < period.EMA_30]) > 0:
            return TradeAction.SELL

        return TradeAction.NONE

    def _ema_alligator_hist_predict(self, df):
        if len(df) < 4:
            return TradeAction.NONE

        period = df[-3:]

        if len(period[period.EMA_5 > period.EMA_8]) > 0 and len(period[period.EMA_8 > period.EMA_13]) > 0:
            return TradeAction.BUY
        elif len(period[period.EMA_5 < period.EMA_8]) > 0 and len(period[period.EMA_8 < period.EMA_13]) > 0:
            return TradeAction.SELL

        return TradeAction.NONE

    def _ema_alligator_predict(self, df):
        current_ema_13 = df.EMA_13.iloc[-1]
        current_ema_8 = df.EMA_8.iloc[-1]
        current_ema_5 = df.EMA_5.iloc[-1]

        if current_ema_5 > current_ema_8 > current_ema_13:
            return TradeAction.BUY
        elif current_ema_13 > current_ema_8 > current_ema_5:
            return TradeAction.SELL

        return TradeAction.NONE

    def _ema_10_50_diff(self, df):
        period = df[-3:]
        ema_diff = period.EMA_10 - period.EMA_50

        if ema_diff.iloc[-1] > 0:
            if ema_diff.iloc[-1] > ema_diff[-3:-1].max():
                return TradeAction.BUY
        else:
            if ema_diff.iloc[-1] < ema_diff[-3:-1].min():
                return TradeAction.SELL

        return TradeAction.NONE

    def _ema_20_close(self, df):
        if len(df) < 2:
            return TradeAction.NONE

        period = df[-2:]

        if len(period[period.EMA_20 < period.close]) == len(period):
            return TradeAction.BUY
        elif len(period[period.EMA_20 > period.close]) == len(period):
            return TradeAction.SELL

        return TradeAction.NONE

    def _smma_20_close(self, df):
        if len(df) < 2:
            return TradeAction.NONE

        period = df[-2:]

        if len(period[period.SMMA_20 < period.close]) == len(period):
            return TradeAction.BUY
        elif len(period[period.SMMA_20 > period.close]) == len(period):
            return TradeAction.SELL

        return TradeAction.NONE

    def _ema_20_smma_20(self, df):

        if len(df) < 2:
            return TradeAction.NONE

        period = df[-2:]

        if len(period[period.EMA_20 > period.SMMA_20]) == len(period):
            return TradeAction.BUY
        elif len(period[period.EMA_20 < period.SMMA_20]) == len(period):
            return TradeAction.SELL

        return TradeAction.NONE

    def _ema_20_channel(self, df):
        period_len = 5
        if len(df) < period_len:
            return TradeAction.NONE

        period = df[-1 * period_len:-2]

        current_close = df.close.iloc[-1]
        before_low = df.low.iloc[-2]
        before_high = df.high.iloc[-2]
        current_ema_high = df.EMA_20_HIGH.iloc[-1]
        before_ema_high = df.EMA_20_HIGH.iloc[-2]
        current_ema_low = df.EMA_20_LOW.iloc[-1]
        before_ema_low = df.EMA_20_LOW.iloc[-2]

        if current_close > current_ema_low and before_low < before_ema_low and len(
                period[period.close > period.EMA_20_LOW]):
            return TradeAction.BUY
        elif current_close < current_ema_high and before_high > before_ema_high and len(
                period[period.close < period.EMA_20_HIGH]):
            return TradeAction.SELL

        return TradeAction.NONE

    def _rsi_predict(self, df):
        current_rsi = df.RSI.iloc[-1]
        if current_rsi < 50:
            return TradeAction.SELL
        elif current_rsi > 50:
            return TradeAction.BUY

        return TradeAction.NONE

    def _rsi_limit_predict(self, df):
        return self._oscillator_limit(df, "RSI", 50, 70, 30)

    def _rsi_limit_predict_4h(self, df):
        df4h = self.convert_1h_to_4h(df)
        return self._oscillator_limit(df4h, "RSI", 50, 70, 30)

    def _williams_limit_predict(self, df):
        return self._oscillator_limit(df, "WILLIAMS", -50, -20, -80)

    def _rsi_break_predict(self, df):
        return self._oscillator_break(df, "RSI", 50, 50)

    def _rsi_break_30_70_predict(self, df):
        return self._oscillator_break(df, "RSI", 70, 30)

    def _williams_break_predict(self, df):
        return self._oscillator_break(df, "WILLIAMS", -50, -50)

    @staticmethod
    def _oscillator_break(df, name: str, upper_line: int, lower_line: int):
        if len(df) <= 4:
            return TradeAction.NONE

        period = df[-3:-1]
        current_rsi = df[name].iloc[-1]
        if current_rsi >= lower_line and len(period[period[name] < lower_line]) > 0:
            return TradeAction.BUY
        elif current_rsi <= upper_line and len(period[period[name] > upper_line]) > 0:
            return TradeAction.SELL

        return TradeAction.NONE

    @staticmethod
    def _oscillator_limit(df, name: str, middle_line: int, upper_limit: int, lower_limit: int):
        if len(df) == 0:
            return TradeAction.NONE

        current_rsi = df[name].iloc[-1]
        if middle_line > current_rsi > lower_limit:
            return TradeAction.SELL
        elif upper_limit > current_rsi > middle_line:
            return TradeAction.BUY

        return TradeAction.NONE

    def _convergence_predict(self, df, indicator_name, b4after: int = 3, look_back: int = 20):
        pv = PivotScanner(be4after=b4after, lookback=look_back)

        pv.scan(df)
        highs = df[df.pivot_point == 3.0]
        sorted_highs = highs.sort_values(by=["high"])

        if len(highs) >= 2 and sorted_highs[-1:].index.item() > sorted_highs[-2:-1].index.item():
            # Aufwärtstrend
            if sorted_highs[-1:][indicator_name].item() < sorted_highs[-2:-1][indicator_name].item():
                return TradeAction.SELL

        lows = df[df.pivot_point == 1.0]
        sorted_lows = lows.sort_values(by=["low"])
        if len(lows) >= 2 and sorted_lows[:1].index.item() < sorted_lows[1:2].index.item():
            # Aufwärtstrend
            if sorted_lows[:1][indicator_name].item() > sorted_lows[1:2][indicator_name].item():
                return TradeAction.BUY

        return TradeAction.NONE

    def _rsi_convergence_predict5(self, df):
        return self._convergence_predict(df, "RSI", 5)

    def _rsi_convergence_predict5_30(self, df):
        return self._convergence_predict(df, "RSI", 5, look_back=30)

    def _rsi_convergence_predict5_40(self, df):
        return self._convergence_predict(df, "RSI", 5, look_back=40)

    def _rsi_convergence_predict7(self, df):
        return self._convergence_predict(df, "RSI", 7)

    def _rsi_convergence_predict3(self, df):
        return self._convergence_predict(df, "RSI")

    def _cci_predict(self, df):
        cci = df.CCI.iloc[-1]

        if cci > 100:
            return TradeAction.BUY
        elif cci < -100:
            return TradeAction.SELL

        return TradeAction.NONE

    def _psar_predict(self, df):
        psar = df.PSAR.iloc[-1]
        ema_20 = df.EMA_20.iloc[-1]
        close = df.close.iloc[-1]

        if psar < ema_20 and close > ema_20 and psar < close:
            return TradeAction.BUY
        elif psar > ema_20 and close < ema_20 and psar > close:
            return TradeAction.SELL

        return TradeAction.NONE

    def _psar_change_predict(self, df):
        psar = df.PSAR.iloc[-1]
        close = df.close.iloc[-1]
        period = df[-3:-1]

        if psar < close and len(period[period.PSAR > period.close]) > 0:
            return TradeAction.BUY
        elif psar > close and len(period[period.PSAR < period.close]) > 0:
            return TradeAction.SELL

        return TradeAction.NONE

    def _candle_predict(self, df):
        c = Candle(df[-1:])

        if c.direction() == Direction.Bullish:
            return TradeAction.BUY
        else:
            return TradeAction.SELL

    def _candle_pattern_predict(self, df):
        if len(df) < 3:
            return TradeAction.NONE

        c = MultiCandle(df)
        t = c.get_type()

        if t == MultiCandleType.MorningStart or t == MultiCandleType.BullishEngulfing:
            return TradeAction.BUY
        elif t == MultiCandleType.EveningStar or t == MultiCandleType.BearishEngulfing:
            return TradeAction.SELL

        return TradeAction.NONE

    def _macd_predict(self, df):
        current_macd = df.MACD.iloc[-1]
        current_signal = df.SIGNAL.iloc[-1]
        if current_macd > current_signal:
            return TradeAction.BUY
        else:
            return TradeAction.SELL

    def _macd_convergence_predict(self, df):
        return self._convergence_predict(df, "MACD")

    def _macd_predict_zero_line(self, df):
        current_macd = df.MACD.iloc[-1]
        current_signal = df.SIGNAL.iloc[-1]
        if current_macd > current_signal and current_macd > 0:
            return TradeAction.BUY
        elif current_macd < current_signal and current_macd < 0:
            return TradeAction.SELL

        return TradeAction.NONE

    def _macd_crossing_predict(self, df):
        period = df[-4:-1]
        current_macd = df.MACD.iloc[-1]
        current_signal = df.SIGNAL.iloc[-1]
        if current_macd > current_signal:  # MACD größer als SIGNAL
            if len(period[period.MACD < period.SIGNAL]) > 0:
                return TradeAction.BUY
        else:  # SIGNAL größer als MACD
            if len(period[period.MACD > period.SIGNAL]) > 0:
                return TradeAction.SELL

        return TradeAction.NONE

    def _macd_signal_diff_predict(self, df):
        if len(df) < 2:
            return TradeAction.NONE

        current_macd = df.MACD.iloc[-1]
        current_signal = df.SIGNAL.iloc[-1]
        before_macd = df.MACD.iloc[-2]
        before_signal = df.SIGNAL.iloc[-2]
        if current_macd > current_signal and before_macd > before_signal:
            if (current_macd - current_signal) > (before_macd - before_signal):
                return TradeAction.BUY
        elif current_macd < current_signal and before_macd < before_signal:
            if (current_signal - current_macd) > (before_signal - before_macd):
                return TradeAction.SELL

        return TradeAction.NONE

    def _bb_predict(self, df):
        bb_middle = df.BB_MIDDLE.iloc[-1]
        bb_upper = df.BB_UPPER.iloc[-1]
        bb_lower = df.BB_LOWER.iloc[-1]
        close = df.close.iloc[-1]

        if bb_middle < close < bb_upper:
            return TradeAction.BUY
        elif bb_middle > close > bb_lower:
            return TradeAction.SELL

        return TradeAction.NONE

    def _bb_middle_cross_predict(self, df):
        bb_middle = df.BB_MIDDLE.iloc[-1]
        close = df.close.iloc[-1]
        period = df[-3:-1]

        if close > bb_middle and len(period[period.close < period.BB_MIDDLE]) > 0:
            return TradeAction.BUY
        elif close < bb_middle and len(period[close > period.BB_MIDDLE]) > 0:
            return TradeAction.SELL

        return TradeAction.NONE

    def _bb_border_cross_predict(self, df):
        bb_lower = df.BB_LOWER.iloc[-1]
        bb_upper = df.BB_UPPER.iloc[-1]
        close = df.close.iloc[-1]
        period = df[-3:-1]

        if close > bb_lower and len(period[period.close < period.BB_LOWER]) > 0:
            return TradeAction.BUY
        elif close < bb_upper and len(period[close > period.BB_UPPER]) > 0:
            return TradeAction.SELL

        return TradeAction.NONE

    def _adx_predict(self, df):
        adx = df.ADX.iloc[-1]

        if adx > 25:
            return TradeAction.BOTH

        return TradeAction.NONE

    def _adx_slope_predict(self, df):
        if len(df) < 2:
            return TradeAction.NONE

        current_adx = df.ADX.iloc[-1]
        before_adx = df.ADX.iloc[-2]

        if current_adx > 20 and before_adx < current_adx:
            return TradeAction.BOTH

        return TradeAction.NONE

    def _adx_slope_predict_21(self, df):
        if len(df) < 2:
            return TradeAction.NONE

        current_adx = df.ADX_21.iloc[-1]
        before_adx = df.ADX_21.iloc[-2]

        if current_adx > 20 and before_adx < current_adx:
            return TradeAction.BOTH

        return TradeAction.NONE

    def _adx_slope_predict_48(self, df):
        if len(df) < 2:
            return TradeAction.NONE

        current_adx = df.ADX_48.iloc[-1]
        before_adx = df.ADX_48.iloc[-2]

        if current_adx > 20 and before_adx < current_adx:
            return TradeAction.BOTH

        return TradeAction.NONE

    def _adx__break_predict(self, df):
        if len(df) < 2:
            return TradeAction.NONE

        current_adx = df.ADX.iloc[-1]
        before_adx = df.ADX.iloc[-2]

        if current_adx > 23 and before_adx < current_adx:
            return TradeAction.BOTH

        return TradeAction.NONE

    def _adx_max_predict(self, df):
        return self._oszi_max(df, "ADX", 7, 0.9)

    def _adx_max_predict_4h(self, df):
        df4h = self.convert_1h_to_4h(df)
        return self._oszi_max(df4h, "ADX", 7, 0.9)

    def _adx_max_predict_21(self, df):
        return self._oszi_max(df, "ADX_21", 7, 0.9)

    def _adx_max_predict_48(self, df):
        return self._oszi_max(df, "ADX_48", 7, 0.9)

    def _adx_max_predict2(self, df):
        return self._oszi_max(df, "ADX", 14, 0.8)

    def _oszi_max(self, df, indicator_name, days, ratio):
        if len(df) == 0:
            return TradeAction.NONE

        current = df[indicator_name].iloc[-1]
        max = df[(days * 24) * -1:][indicator_name].max()

        if current > max * ratio:
            return TradeAction.NONE

        return TradeAction.BOTH

    def _oszi_min_max(self, df, indicator_name, days, ratio):
        if len(df) == 0:
            return TradeAction.NONE

        current = df[indicator_name].iloc[-1]
        max = df[(days * 24) * -1:][indicator_name].max()
        min = df[(days * 24) * -1:][indicator_name].min()

        if current > max * ratio:
            return TradeAction.NONE
        elif current < min * ratio:
            return TradeAction.NONE

        return TradeAction.BOTH

    def _macd_max_predict(self, df):
        return self._oszi_min_max(df, "MACD", 7, 0.9)

    def _macd_max_predict_4h(self, df):
        return self._oszi_min_max(self.convert_1h_to_4h(df), "MACD", 7, 0.9)

    def _macd_max_predict2(self, df):
        return self._oszi_min_max(df, "MACD", 14, 0.8)

    def _macd_slope_predict(self, df):
        if len(df) < 2:
            return TradeAction.NONE

        current_macd = df.MACD.iloc[-1]
        before_macd = df.MACD.iloc[-2]

        if current_macd > before_macd:
            return TradeAction.BUY
        else:
            return TradeAction.SELL

    def _rsi_smooth_slope_predict(self, df):
        diff = df.RSI_SMOOTH.diff().iloc[-1]
        if diff < 0:
            return TradeAction.SELL
        else:
            return TradeAction.BUY

    def _rsi_smooth_30_70_predict(self, df):
        rsi_smooth = df.RSI_SMOOTH.iloc[-1]
        if rsi_smooth > 70:
            return TradeAction.BUY
        elif rsi_smooth < 30:
            return TradeAction.SELL

        return TradeAction.NONE

    def _tii_50(self, df):
        if len(df) < 2:
            return TradeAction.NONE

        current_tii = df.TII.iloc[-1]
        before_tii = df.TII.iloc[-2]
        if current_tii > 50 and before_tii < 50:
            return TradeAction.BUY
        elif current_tii < 50 and before_tii > 50:
            return TradeAction.SELL

        return TradeAction.NONE

    def _tii_20_80(self, df):
        if len(df) < 2:
            return TradeAction.NONE

        current_tii = df.TII.iloc[-1]
        before_tii = df.TII.iloc[-2]
        if current_tii > 20 > before_tii:
            return TradeAction.BUY
        elif current_tii < 80 < before_tii:
            return TradeAction.SELL

        return TradeAction.NONE

    def _ichimoku_predict(self, df):

        actions = []
        actions.append(self._ichimoku_tenkan_kijun_predict(df))
        actions.append(self._ichimoku_cloud_predict(df))

        if actions.count(TradeAction.BUY) == len(actions):
            return TradeAction.BUY
        elif actions.count(TradeAction.SELL) == len(actions):
            return TradeAction.SELL

        return TradeAction.NONE

    def _ichimoku_kijun_close_predict(self, df):
        # Kijun Sen. Allgemein gilt für diesen zunächst, dass bei Kursen oberhalb der
        # Linie nur Long-Trades vorgenommen werden sollten, und unterhalb entsprechend nur Short-Trades.
        kijun = df.KIJUN.iloc[-1]
        close = df.close.iloc[-1]

        if close > kijun:
            return TradeAction.BUY
        else:
            return TradeAction.SELL

    def _ichimoku_kijun_close_predict_4h(self, df):
        # Kijun Sen. Allgemein gilt für diesen zunächst, dass bei Kursen oberhalb der
        # Linie nur Long-Trades vorgenommen werden sollten, und unterhalb entsprechend nur Short-Trades.
        df4h = self.convert_1h_to_4h(df)

        if len(df4h) == 0:
            return TradeAction.NONE

        kijun = df4h.KIJUN.iloc[-1]
        close = df.close.iloc[-1]

        if close > kijun:
            return TradeAction.BUY
        else:
            return TradeAction.SELL

    def _ichimoku_kijun_close_cross_predict(self, df):
        # Kijun Sen. Allgemein gilt für diesen zunächst, dass bei Kursen oberhalb der
        # Linie nur Long-Trades vorgenommen werden sollten, und unterhalb entsprechend nur Short-Trades.
        kijun = df.KIJUN.iloc[-1]
        close = df.close.iloc[-1]
        period = df[-3:-1]

        if close > kijun and len(period[period.close < period.KIJUN]) > 0:
            return TradeAction.BUY
        elif close < kijun and len(period[period.close > period.KIJUN]) > 0:
            return TradeAction.SELL

        return TradeAction.NONE

    def _ichimoku_cloud_predict(self, df):
        senkou_a = df.SENKOU_A.iloc[-1]
        senkou_b = df.SENKOU_B.iloc[-1]
        close = df.close[-1:].item()

        if senkou_a > senkou_b:
            if close > senkou_a:
                return TradeAction.BUY
        else:
            if close < senkou_a:
                return TradeAction.SELL

        return TradeAction.NONE

    def _ichimoku_tenkan_kijun_predict(self, df):
        period = df[-4:-1]
        tenkan = df.TENKAN.iloc[-1]
        kijun = df.KIJUN.iloc[-1]

        if tenkan > kijun:
            if len(period[period.TENKAN < period.KIJUN]) > 0:
                return TradeAction.BUY
        else:
            if len(period[period.TENKAN > period.KIJUN]) > 0:
                return TradeAction.SELL

        return TradeAction.NONE

    def _ichimoku_chikou_predict(self, df):
        """
                Wenn Chickou über Close -> BUY
                Wenn Chickou unter Close -> SELL

                Args:
                df (DataFrame): Ein DataFrame mit den EMA-Werten für verschiedene Perioden.

                Returns:
                TradeAction: Eine Handlungsempfehlung, entweder "BUY", "SELL" oder "NONE".
                """

        if len(df[-27:]) < 27:
            return TradeAction.NONE

        chikou = df.CHIKOU.iloc[-27]
        close = df.close.iloc[-27]

        if chikou > close:
            return TradeAction.BUY
        else:
            return TradeAction.SELL

    def _ichimoku_cloud_thickness_predict(self, df):
        """
           Wenn die Cloudn dicker wird, kann ein Handel eröffne werden

           Args:
           df (DataFrame): Ein DataFrame mit den EMA-Werten für verschiedene Perioden.

           Returns:
           TradeAction: Eine Handlungsempfehlung, entweder "BUY", "SELL" oder "NONE".
           """
        period = df[-4:]
        cloud_thickness = period.SENKOU_A - period.SENKOU_B

        if cloud_thickness.iloc[-1] > 0:
            if cloud_thickness.iloc[-1] > cloud_thickness[-4:-1].max():
                return TradeAction.BUY
        else:
            if cloud_thickness.iloc[-1] < cloud_thickness[-4:-1].min():
                return TradeAction.SELL

        return TradeAction.NONE
    # endregion
