from typing import List

import pandas as pd
from pandas import DataFrame, Series

from BL import DataProcessor
from BL.candle import Candle, Direction, MultiCandle, MultiCandleType, CandleType
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
    RSI_SLOPE = "rsi_slope"
    RSI_CONVERGENCE = "rsi_convergence"
    RSI_CONVERGENCE_4H = "rsi_convergence_4h"
    RSI_CONVERGENCE5 = "rsi_convergence5"
    RSI_CONVERGENCE5_30 = "rsi_convergence5_30"
    RSI_CONVERGENCE5_40 = "rsi_convergence5_40"
    RSI_CONVERGENCE7 = "rsi_convergence7"
    # endregion
    # region Williams
    WILLIAMS_LIMIT = "williams_limit"
    WILLIAMS_BREAK = "williams_break"
    WILLIAMS_LIMIT_4H = "williams_limit_4h"
    WILLIAMS_BREAK_4H = "williams_break_4h"
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
    MACD_MAX_2 = "macd_max_2"
    MACD_MAX_4H = "macd_max_4h"
    MACD_MAX_12H = "macd_max_12h"
    MACD_SLOPE = "macd_slope"
    MACD_SLOPE_4H = "macd_slope_4h"
    # EMA
    EMA = "ema"
    EMA_10_SLOPE = "ema_10_slope"
    EMA_30_SLOPE = "ema_30_slope"
    EMA_50_SLOPE = "ema_50_slope"
    EMA_HIST = "ema_hist"
    EMA_ALLIGATOR = "ema_alligator"
    EMA_ALLIGATOR_HIST = "ema_alligator_hist"
    EMA10_50 = "ema_10_50"
    EMA20_CLOSE = "ema_20_close"
    EMA30_CLOSE = "ema_30_close"
    EMA50_CLOSE = "ema_50_close"
    SMMA20_CLOSE = "smma_20_close"
    EMA20_SMMA20 = "ema_20_smma_20"
    EMA_20_CHANNEL = "ema_20_channel"

    #PIVOT
    PIVOT_BOUNCE = "pivot_bounce"
    PIVOT_BOUNCE_4H = "pivot_bounce_4h"
    PIVOT_BREAKOUT = "pivot_breakout"
    PIVOT_SR_TRADING = "privot_sr_trading"
    PIVOT_SR_TRADING_4H = "privot_sr_trading_4h"
    PIVOT_EMA_20_CROSS = "pivot_bounce"

    #Fibonacci
    PIVOT_FIB_BOUNCE = "pivot_fib_bounce"
    PIVOT_FIB_BOUNCE_4H = "pivot_fib_bounce_4h"
    PIVOT_FIB_SR_TRADING = "privot_fib_sr_trading"
    PIVOT_FIB_SR_TRADING_4H = "privot_fib_sr_trading_4h"

    # CCI
    CCI = "cci"
    CCI_4h = "cci_4h"
    CCI_CONV = "cci_convergence"
    CCI_CROSS = "cci_cross"
    CCI_CROSS_4H = "cci_cross_4h"


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
    SUPER_TREND = "super_trend"

    CANDLE = "candle"
    CANDLEPATTERN = "candle_pattern"
    CANDLE_4H = "candle_4h"
    CANDLE_TYPE = "candle_type"
    CANDLE_TYPE_HAMMER = "candle_type_hammer"
    CANDLE_TYPE_SS_HM = "candle_type_ss_hm"
    CANDLE_TYPE_4H = "candle_type_4h"
    # Bollinger
    BB = "bb"
    BB_4H = "bb_4h"
    BB_MIDDLE_CROSS = "bb_middle_crossing"
    BB_MIDDLE_CROSS_4H = "bb_middle_crossing_4h"
    BB_BORDER_CROSS = "bb_border_crossing"
    BB_SQUEEZE = "bb_sqeeze"
    BB_SQUEEZE_BOTH = "bb_sqeeze_both_direction"
    # ICHIMOKU
    ICHIMOKU = "ichi"
    ICHIMOKU_KIJUN_CONFIRM = "ichi_kijun_confirm"
    ICHIMOKU_KIJUN_CONFIRM_4H = "ichi_kijun_confirm_4h"
    ICHIMOKU_KIJUN_CROSS_CONFIRM = "ichi_kijun_cross_confirm"
    ICHIMOKU_CLOUD_CONFIRM = "ichi_cloud_confirm"
    ICHIMOKU_CLOUD_THICKNESS = "ichi_cloud_thickness"

    # endregion

    # region Constructor
    def __init__(self, tracer: Tracer = ConsoleTracer(), dp = DataProcessor()):
        self._indicators = []
        self._dp = dp
        self._indicator_confirm_factor = 0.7

        # RSI
        self._add_indicator(self.RSI, self._rsi_predict)
        self._add_indicator(self.RSI_LIMIT, self._rsi_limit_predict)
        self._add_indicator(self.RSI_LIMIT_4H, self._rsi_limit_predict_4h)
        self._add_indicator(self.RSI_BREAK, self._rsi_break_predict)
        #self._add_indicator(self.RSI_BREAK3070, self._rsi_break_30_70_predict) #BAD
        self._add_indicator(self.RSI_CONVERGENCE, self._rsi_convergence_predict3)
        self._add_indicator(self.RSI_CONVERGENCE_4H, self._rsi_convergence_predict3_4h)
        #self._add_indicator(self.RSI_CONVERGENCE5, self._rsi_convergence_predict5)
        #self._add_indicator(self.RSI_CONVERGENCE5_30, self._rsi_convergence_predict5_30) #BAD
        self._add_indicator(self.RSI_CONVERGENCE5_40, self._rsi_convergence_predict5_40)
        #self._add_indicator(self.RSI_CONVERGENCE7, self._rsi_convergence_predict7)
        #self._add_indicator(self.RSI30_70, self._rsi_smooth_30_70_predict) #BAD
        self._add_indicator(self.RSI_SLOPE, self._rsi_smooth_slope_predict)
        self._add_indicator(self.RSI_BREAK_4H, self._rsi_break_predict_4h)

        #self._add_indicator(self.TII_50, self._tii_50) #BAD
        #self._add_indicator(self.TII_20_80, self._tii_20_80) #BAD

        # Williams
        self._add_indicator(self.WILLIAMS_BREAK, self._williams_break_predict)
        self._add_indicator(self.WILLIAMS_BREAK_4H, self._williams_break_predict_4h)
        self._add_indicator(self.WILLIAMS_LIMIT, self._williams_limit_predict)
        self._add_indicator(self.WILLIAMS_LIMIT_4H, self._williams_limit_predict_4h)

        # MACD
        self._add_indicator(self.MACD, self._macd_predict)
        self._add_indicator(self.MACD_SLOPE, self._macd_slope_predict)
        self._add_indicator(self.MACD_SLOPE_4H, self._macd_slope_predict_4h)
        self._add_indicator(self.MACD_MAX, self._macd_max_predict)
        self._add_indicator(self.MACD_MAX_2, self._macd_max_predict2)
        self._add_indicator(self.MACD_MAX_4H, self._macd_max_predict_4h)
        self._add_indicator(self.MACD_MAX_12H, self._macd_max_predict_12h)
        self._add_indicator(self.MACD_ZERO, self._macd_predict_zero_line)
        self._add_indicator(self.MACDCROSSING, self._macd_crossing_predict)
        self._add_indicator(self.MACD_CONVERGENCE, self._macd_convergence_predict)
        self._add_indicator(self.MACDSINGALDIFF, self._macd_signal_diff_predict)

        # EMA
        self._add_indicator(self.EMA, self._ema_predict)
        self._add_indicator(self.EMA_10_SLOPE, self._ema_10_slope)
        self._add_indicator(self.EMA_30_SLOPE, self._ema_30_slope)
        self._add_indicator(self.EMA_50_SLOPE, self._ema_50_slope)

        self._add_indicator(self.EMA_ALLIGATOR, self._ema_alligator_predict)
        self._add_indicator(self.EMA_HIST, self._ema_hist_predict)
        self._add_indicator(self.EMA_ALLIGATOR_HIST, self._ema_alligator_hist_predict)
        self._add_indicator(self.EMA10_50, self._ema_10_50_diff)
        self._add_indicator(self.EMA20_CLOSE, self._ema_20_close)
        self._add_indicator(self.EMA30_CLOSE, self._ema_30_close)
        self._add_indicator(self.EMA50_CLOSE, self._ema_50_close)
        self._add_indicator(self.SMMA20_CLOSE, self._smma_20_close)
        self._add_indicator(self.EMA20_SMMA20, self._ema_20_smma_20)
        self._add_indicator(self.EMA_20_CHANNEL, self._ema_20_channel)

        #Pivoting
        self._add_indicator(self.PIVOT_BOUNCE, self._pivot_bounce)
        #self._add_indicator(self.PIVOT_BOUNCE_4H, self._pivot_bounce_4h)
        self._add_indicator(self.PIVOT_BREAKOUT, self._pivot_breakout)
        self._add_indicator(self.PIVOT_SR_TRADING, self._pivot_sr_trading)
        self._add_indicator(self.PIVOT_SR_TRADING_4H, self._pivot_sr_trading_4h)
        self._add_indicator(self.PIVOT_EMA_20_CROSS, self._pivot_ema_20_cross)

        #Fibonacci
        self._add_indicator(self.PIVOT_FIB_BOUNCE, self._pivot_fib_bounce)
        self._add_indicator(self.PIVOT_FIB_SR_TRADING, self._pivot_fib_sr_trading)

        # ADX
        self._add_indicator(self.ADX, self._adx_predict)
        self._add_indicator(self.ADX_SLOPE, self._adx_slope_predict)
        #self._add_indicator(self.ADX_SLOPE_21, self._adx_slope_predict_21) #BAD
        #self._add_indicator(self.ADX_SLOPE_48, self._adx_slope_predict_48) #BAD
        self._add_indicator(self.ADX_MAX, self._adx_max_predict)
        self._add_indicator(self.ADX_MAX_4H, self._adx_max_predict_4h)
        self._add_indicator(self.ADX_MAX_21, self._adx_max_predict_21)
        self._add_indicator(self.ADX_MAX_48, self._adx_max_predict_48)
        self._add_indicator(self.ADX_MAX2, self._adx_max_predict2)
        self._add_indicator(self.ADX_BREAK, self._adx__break_predict)

        #CCI
        self._add_indicator(self.CCI, self._cci_predict)
        self._add_indicator(self.CCI_4h, self._cci_predict_4h)
        #self._add_indicator(self.CCI_CONV, self._cci_convergence)
        self._add_indicator(self.CCI_CROSS, self._cci_zero_cross)
        #self._add_indicator(self.CCI_CROSS_4H, self._cci_zero_cross_4h)


        # Others

        self._add_indicator(self.CANDLE, self._candle_predict)
        self._add_indicator(self.CANDLEPATTERN, self._candle_pattern_predict)
        self._add_indicator(self.CANDLE_4H, self._candle_predict_4h)
        self._add_indicator(self.CANDLE_TYPE, self._candle_type_predict)
        #self._add_indicator(self.CANDLE_TYPE_HAMMER, self._candle_hammer_predict)
        #self._add_indicator(self.CANDLE_TYPE_SS_HM, self._candle_shootingstar_hanging_man_predict)
        self._add_indicator(self.CANDLE_TYPE_4H, self._candle_type_predict_4h)
        #self._add_indicator(self.SUPER_TREND, self._super_trend)



        # PSAR
        self._add_indicator(self.PSAR, self._psar_predict)
        self._add_indicator(self.PSAR_CHANGE, self._psar_change_predict)

        # Bollinger
        self._add_indicator(self.BB, self._bb_predict)
        self._add_indicator(self.BB_4H, self._bb_predict_4h)
        self._add_indicator(self.BB_MIDDLE_CROSS, self._bb_middle_cross_predict)
        self._add_indicator(self.BB_MIDDLE_CROSS_4H, self._bb_middle_cross_predict_4h)
        self._add_indicator(self.BB_SQUEEZE, self._bb_squeeze)
        self._add_indicator(self.BB_SQUEEZE_BOTH, self._bb_squeeze_both)

        #self._add_indicator(self.BB_BORDER_CROSS, self._bb_border_cross_predict) #BAD

        # ICHIMOKU
        #self._add_indicator(self.ICHIMOKU, self._ichimoku_predict)
        self._add_indicator(self.ICHIMOKU_KIJUN_CONFIRM, self._ichimoku_kijun_close_predict)
        self._add_indicator(self.ICHIMOKU_KIJUN_CONFIRM_4H, self._ichimoku_kijun_close_predict_4h)
        self._add_indicator(self.ICHIMOKU_KIJUN_CROSS_CONFIRM, self._ichimoku_kijun_close_cross_predict)
        #self._add_indicator(self.ICHIMOKU_CLOUD_CONFIRM, self._ichimoku_cloud_thickness_predict)
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
            'low': 'min',  # Höchster Kurs in der 4-Stunden-Periode
            'close': 'last',  # Höchster Kurs in der 4-Stunden-Periode
            'date_index': 'first'  # Erstes Zeitstempel in der 4-Stunden-Periode
        }).reset_index(drop=True)
        df_4h.dropna(inplace=True)
        df_4h.reset_index(inplace=True)

        df_4h = df_4h.filter(["open", "low", "high", "close"])
        self._dp.addSignals_big_tf(df_4h)

        return df_4h.dropna()

    def convert_1h_to_12h(self, one_h_df: DataFrame):
        if len(one_h_df) == 0:
            return DataFrame()

        one_h_df['date_index'] = pd.to_datetime(one_h_df['date'])
        # Gruppieren nach 4 Stunden und Aggregation der Kursdaten
        df_12h: DataFrame = one_h_df.groupby(pd.Grouper(key='date_index', freq='12H')).agg({
            'open': 'first',  # Erster Kurs in der 4-Stunden-Periode
            'high': 'max',  # Höchster Kurs in der 4-Stunden-Periode
            'low': 'min',  # Höchster Kurs in der 4-Stunden-Periode
            'close': 'last',  # Höchster Kurs in der 4-Stunden-Periode
            'date_index': 'first'  # Erstes Zeitstempel in der 4-Stunden-Periode
        }).reset_index(drop=True)
        df_12h.dropna(inplace=True)
        df_12h.reset_index(inplace=True)

        df_12h = df_12h.filter(["open", "low", "high", "close"])
        self._dp.addSignals_big_tf(df_12h)

        return df_12h.dropna()

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

        if predict_values.count(TradeAction.BOTH) == len(predict_values):
            return TradeAction.BOTH

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

    def _ema_10_slope(self, df):
        return  self._check_slope(df.EMA_10)

    def _ema_30_slope(self, df):
        return self._check_slope(df.EMA_30)

    def _ema_50_slope(self, df):
        return self._check_slope(df.EMA_50)

    def _check_slope(self, s:Series):

        diffs = s.diff()
        pos_sloap = diffs > 0
        if pos_sloap[-3:].all():
            return TradeAction.BUY

        neg_sloap = diffs < 0

        if neg_sloap[-3:].all():
            return TradeAction.SELL

        return TradeAction.NONE

    def _super_trend(self, df):
        multiplier = 3.0
        df = df.copy()
        # Calculate HL2 (average of high and low)
        df['hl2'] = (df['high'] + df['low']) / 2

        # Calculate the Supertrend levels
        df['upperband'] = df['hl2'] - (multiplier * df['ATR'])
        df['lowerband'] = df['hl2'] + (multiplier * df['ATR'])

        # Initialize the trend column
        df['trend'] = 0

        # Determine the trend direction based on previous close and upper/lower bands
        for i in range(1, len(df)):
            if df['close'].iloc[i - 1] > df['upperband'].iloc[i - 1]:
                df['trend'].iloc[i] = 1  # Uptrend
            elif df['close'].iloc[i - 1] < df['lowerband'].iloc[i - 1]:
                df['trend'].iloc[i] = -1  # Downtrend
            else:
                df['trend'].iloc[i] = df['trend'].iloc[i - 1]  # No change

            # Adjust the upper and lower bands based on the trend
            if df['trend'].iloc[i] == 1 and df['upperband'].iloc[i] < df['upperband'].iloc[i - 1]:
                df['upperband'].iloc[i] = df['upperband'].iloc[i - 1]
            if df['trend'].iloc[i] == -1 and df['lowerband'].iloc[i] > df['lowerband'].iloc[i - 1]:
                df['lowerband'].iloc[i] = df['lowerband'].iloc[i - 1]

        # Evaluate the last row for buy/sell signal
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2] if len(df) > 1 else last_row

        if last_row['trend'] == 1 and prev_row['trend'] == -1:
            return TradeAction.BUY
        elif last_row['trend'] == -1 and prev_row['trend'] == 1:
            return TradeAction.SELL
        else:
            return TradeAction.NONE

    def _pivot_bounce(self, df):
        return self._pivot_bounce_bl(df["close"], df["PIVOT"])

    def _pivot_fib_bounce(self, df):
        return self._pivot_bounce_bl(df["close"], df["PIVOT_FIB"])

    def _pivot_bounce_bl(self, close:Series, pivot:Series):
        if len(pivot) < 2:
            return TradeAction.NONE

        if close.iloc[-2] < pivot.iloc[-2] and close.iloc[-1] > \
                pivot.iloc[-1]:
            return TradeAction.BUY
        elif close.iloc[-2] > pivot.iloc[-2] and close.iloc[-1] < \
                pivot.iloc[-1]:
            return TradeAction.SELL

        return TradeAction.NONE

    def _pivot_ema_20_cross(self, df):

        if len(df) < 2:
            return TradeAction.NONE
        ema = df["EMA_20"]
        pivot = df["PIVOT"]

        if ema.iloc[-2] < pivot.iloc[-2] and ema.iloc[-1] > \
                pivot.iloc[-1]:
            return TradeAction.BUY
        elif ema.iloc[-2] > pivot.iloc[-2] and ema.iloc[-1] < \
                pivot.iloc[-1]:
            return TradeAction.SELL

        return TradeAction.NONE

    def _pivot_bounce_4h(self, df):
        return self._pivot_bounce(self.convert_1h_to_4h(df))

    def _pivot_breakout(self,df):

        if df['close'].iloc[-1] > df['R1'].iloc[-1]:
            return TradeAction.BUY
        elif df['close'].iloc[-1] < df['S1'].iloc[-1]:
            return TradeAction.SELL
        return TradeAction.NONE

    def _pivot_sr_trading(self, df) -> str:
        return self._pivot_sr_trading_bl(low=df["low"],high= df["high"],close= df["close"], s1= df["S1"], r1=df["R1"])

    def _pivot_fib_sr_trading(self, df) -> str:
        return self._pivot_sr_trading_bl(low=df["low"], high=df["high"], close=df["close"], s1=df["S1_FIB"], r1=df["R1_FIB"])

    def _pivot_sr_trading_bl(self,low:Series, high:Series,close:Series, s1:Series, r1:Series):
        if len(s1) == 0:
            return TradeAction.NONE

        if low.iloc[-1] <= s1.iloc[-1] and close.iloc[-1] > s1.iloc[-1]:
            return TradeAction.BUY

        elif high.iloc[-1] >= r1.iloc[-1] and close.iloc[-1] < r1.iloc[-1]:
            return TradeAction.SELL

        return TradeAction.NONE

    def _pivot_sr_trading_4h(self, df):
        return self._pivot_sr_trading(self.convert_1h_to_4h(df))

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

    def _ema_10_30_diff_max(self, df:DataFrame):
        return self._line_diff_max(df.EMA_10,df.EMA_30)

    def _line_diff_max(self, line1: Series,  line2: Series, ratio: float = 0.7):
        diff = abs(line1 - line2)
        max_diff = diff.max()

        if abs(diff.iloc[-1]) > max_diff * ratio:
            return TradeAction.NONE

        return TradeAction.BOTH

    def _ema_20_close(self, df):
        if len(df) < 2:
            return TradeAction.NONE

        period = df[-2:]

        if len(period[period.EMA_20 < period.close]) == len(period):
            return TradeAction.BUY
        elif len(period[period.EMA_20 > period.close]) == len(period):
            return TradeAction.SELL

        return TradeAction.NONE

    def _ema_30_close(self, df):
        if len(df) < 2:
            return TradeAction.NONE

        period = df[-2:]

        if len(period[period.EMA_30 < period.close]) == len(period):
            return TradeAction.BUY
        elif len(period[period.EMA_30 > period.close]) == len(period):
            return TradeAction.SELL

        return TradeAction.NONE

    def _ema_50_close(self, df):
        if len(df) < 2:
            return TradeAction.NONE

        period = df[-2:]

        if len(period[period.EMA_50 < period.close]) == len(period):
            return TradeAction.BUY
        elif len(period[period.EMA_50 > period.close]) == len(period):
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

    def _williams_limit_predict_4h(self, df):
        return self._williams_limit_predict(self.convert_1h_to_4h(df))

    def _rsi_break_predict(self, df):
        return self._oscillator_break(df, "RSI", 50, 50)

    def _rsi_break_30_70_predict(self, df):
        return self._oscillator_break(df, "RSI", 70, 30)

    def _williams_break_predict(self, df):
        return self._oscillator_break(df, "WILLIAMS", -50, -50)

    def _williams_break_predict_4h(self, df):
        return self._williams_break_predict(self.convert_1h_to_4h(df))

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
        if len(df) < 3:
            return TradeAction.NONE

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

    def _rsi_convergence_predict3_4h(self, df):
        df4h = self.convert_1h_to_4h(df)
        return self._convergence_predict(df4h, "RSI")

    def _cci_predict_4h(self, df):
        df4h = self.convert_1h_to_4h(df)
        return self._cci_predict(df4h)

    def _cci_convergence(self, df):
        return self._convergence_predict(df, "CCI")

    def _cci_zero_cross(self, df):
        if len(df) < 2:
            return TradeAction.NONE

        cci_before = df.CCI.iloc[-2]
        cci_now = df.CCI.iloc[-1]

        if cci_before < 0 < cci_now:
            return TradeAction.BUY
        elif cci_before > 0 > cci_now:
            return TradeAction.SELL

        return TradeAction.NONE

    def _cci_zero_cross_4h(self, df):
        df4h = self.convert_1h_to_4h(df)

        if len(df4h) < 2:
            return TradeAction.NONE

        cci_before = df4h.CCI.iloc[-2]
        cci_now = df4h.CCI.iloc[-1]

        if cci_before < 0 < cci_now:
            return TradeAction.BUY
        elif cci_before > 0 > cci_now:
            return TradeAction.SELL

        return TradeAction.NONE

    def _cci_predict(self, df):
        if len(df) < 1:
            return TradeAction.NONE

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

    def _candle_predict_4h(self, df):
        df4h = self.convert_1h_to_4h(df)
        if len(df4h) < 1:
            return TradeAction.NONE

        c = Candle(df4h[-1:])

        if c.direction() == Direction.Bullish:
            return TradeAction.BUY
        else:
            return TradeAction.SELL

    def _candle_type_predict(self, df):
        if len(df) < 1:
            return TradeAction.NONE

        c = Candle(df[-1:])
        ct = c.candle_type()
        if ct == CandleType.Hammer or ct == CandleType.ImvertedHammer or ct == CandleType.DragonflyDoji:
            return TradeAction.BUY

        if ct == CandleType.HangingMan or ct == CandleType.ShootingStar or ct == CandleType.GraveStoneDoji:
            return TradeAction.SELL

        return TradeAction.NONE

    def _candle_hammer_predict(self, df):
        if len(df) < 1:
            return TradeAction.NONE

        c = Candle(df[-1:])
        ct = c.candle_type()
        if ct == CandleType.Hammer or ct == CandleType.ImvertedHammer:
            return TradeAction.BUY

        return TradeAction.NONE

    def _candle_shootingstar_hanging_man_predict(self, df):
        if len(df) < 1:
            return TradeAction.NONE

        c = Candle(df[-1:])
        ct = c.candle_type()
        if ct == CandleType.ShootingStar or ct == CandleType.HangingMan:
            return TradeAction.SELL

        return TradeAction.NONE

    def _candle_type_predict_4h(self, df):
        df4h = self.convert_1h_to_4h(df)
        return self._candle_type_predict(df4h)

    def _candle_pattern_predict(self, df):
        if len(df) < 3:
            return TradeAction.NONE

        c = MultiCandle(df)
        t = c.get_type()

        if t == MultiCandleType.MorningStart or t == MultiCandleType.BullishEngulfing or t == MultiCandleType.ThreeWhiteSoldiers:
            return TradeAction.BUY
        elif t == MultiCandleType.EveningStar or t == MultiCandleType.BearishEngulfing or t == MultiCandleType.ThreeBlackCrows:
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
        if len(df) == 0:
            return TradeAction.NONE

        bb_middle = df.BB_MIDDLE.iloc[-1]
        bb_upper = df.BB_UPPER.iloc[-1]
        bb_lower = df.BB_LOWER.iloc[-1]
        close = df.close.iloc[-1]

        if bb_middle < close < bb_upper:
            return TradeAction.BUY
        elif bb_middle > close > bb_lower:
            return TradeAction.SELL

        return TradeAction.NONE

    def _bb_predict_4h(self, df):
        return self._bb_predict(self.convert_1h_to_4h(df))


    def _bb_middle_cross_predict(self, df):
        if len(df) < 4:
            return TradeAction.NONE

        bb_middle = df.BB_MIDDLE.iloc[-1]
        close = df.close.iloc[-1]
        period = df[-3:-1]

        if close > bb_middle and len(period[period.close < period.BB_MIDDLE]) > 0:
            return TradeAction.BUY
        elif close < bb_middle and len(period[close > period.BB_MIDDLE]) > 0:
            return TradeAction.SELL

        return TradeAction.NONE

    def _bb_middle_cross_predict_4h(self, df):
        return self._bb_middle_cross_predict(self.convert_1h_to_4h(df))

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

    def _bb_squeeze(self, df):

        # Parameter
        keltFactor = 1.5
        BandsDeviations = 2.0
        BandsPeriod = 20

        df_bb = df.copy()

        # Keltner Channels Breite (Mitte ± ATR * keltFactor)
        df_bb['Keltner Width'] = df_bb['ATR'] * keltFactor

        # Bollinger Bands Breite (obere Band - untere Band)
        df_bb['StdDev'] = df_bb['close'].rolling(window=BandsPeriod).std()
        df_bb['Bollinger Width'] = BandsDeviations * df_bb['StdDev']

        # Bollinger Bands Squeeze
        df_bb['BBS'] = df_bb['Bollinger Width'] / df_bb['Keltner Width']

        # Bedingung für Buy- und Sell-Signal
        df_bb['Buy'] = (df_bb['BBS'] < 1) & (df_bb['CCI'] > 0)
        df_bb['Sell'] = (df_bb['BBS'] < 1) & (df_bb['CCI'] <= 0)

        # Letzter Wert für die Entscheidung
        if df_bb.iloc[-1]['Buy']:
            return TradeAction.BUY
        elif df_bb.iloc[-1]['Sell']:
            return TradeAction.SELL
        else:
            return TradeAction.NONE

    def _bb_squeeze_both(self, df):

        # Parameter
        keltFactor = 1.5
        BandsDeviations = 2.0
        BandsPeriod = 20

        df_bb = df.copy()

        # Keltner Channels Breite (Mitte ± ATR * keltFactor)
        df_bb['Keltner Width'] = df_bb['ATR'] * keltFactor

        # Bollinger Bands Breite (obere Band - untere Band)
        df_bb['StdDev'] = df_bb['close'].rolling(window=BandsPeriod).std()
        df_bb['Bollinger Width'] = BandsDeviations * df_bb['StdDev']

        # Bollinger Bands Squeeze
        df_bb['BBS'] = df_bb['Bollinger Width'] / df_bb['Keltner Width']

        # Letzter Wert für die Entscheidung
        if df_bb.iloc[-1]['BBS'] < 1:
            return TradeAction.BOTH
        else:
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

    def _macd_max_predict_12h(self, df):
        return self._oszi_min_max(self.convert_1h_to_12h(df), "MACD", 7, 0.9)

    def _macd_max_predict2(self, df):
        return self._oszi_min_max(df, "MACD", 7, 0.8)

    def _macd_slope_predict(self, df):
        if len(df) < 2:
            return TradeAction.NONE

        current_macd = df.MACD.iloc[-1]
        before_macd = df.MACD.iloc[-2]

        if current_macd > before_macd:
            return TradeAction.BUY
        else:
            return TradeAction.SELL

    def _macd_slope_predict_4h(self, df:DataFrame):
        return self._macd_slope_predict(self.convert_1h_to_4h(df))


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
