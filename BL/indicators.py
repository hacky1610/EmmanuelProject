from typing import List

from BL.candle import Candle, Direction
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

    #region Static Members
    RSI = "rsi"
    RSI30_70 = "rsi_30_70"
    RSISLOPE = "rsi_slope"
    RSI_CONVERGENCE = "rsi_convergence"
    MACD = "macd"
    MACDCROSSING = "macd_crossing"
    MACD_CONVERGENCE = "macd_convergence"
    ADX = "adx"
    EMA = "ema"
    PSAR = "psar"
    CCI = "cci"
    CANDLE = "candle"
    BB = "bb"
    ICHIMOKU = "ichi"
    ICHIMOKU_KIJUN_CONFIRM = "ichi_kijun_confirm"
    ICHIMOKU_CLOUD_CONFIRM = "ichi_cloud_confirm"
    #endregion

    #region Constructor
    def __init__(self, tracer: Tracer = ConsoleTracer()):
        self._indicators = []
        self._indicator_confirm_factor = 0.7
        self._add_indicator(self.RSI, self._rsi_predict)
        self._add_indicator(self.RSI_CONVERGENCE, self._rsi_convergence_predict)
        self._add_indicator(self.RSI30_70, self._rsi_smooth_30_70_predict)
        self._add_indicator(self.MACD, self._macd_predict)
        self._add_indicator(self.MACDCROSSING, self._macd_crossing_predict)
        self._add_indicator(self.MACD_CONVERGENCE, self._macd_convergence_predict)
        self._add_indicator(self.ADX, self._adx_predict)
        self._add_indicator(self.EMA, self._ema_predict)
        self._add_indicator(self.BB, self._bb_predict)
        self._add_indicator(self.CANDLE, self._candle_predict)
        self._add_indicator(self.CCI, self._cci_predict)
        self._add_indicator(self.RSISLOPE, self._rsi_smooth_slope_predict)
        self._add_indicator(self.PSAR, self._psar_predict)
        self._add_indicator(self.ICHIMOKU, self._ichimoku_predict)
        self._add_indicator(self.ICHIMOKU_KIJUN_CONFIRM, self._ichimoku_kijun_close_predict)
        self._add_indicator(self.ICHIMOKU_CLOUD_CONFIRM, self._ichimoku_cloud_thickness_predict)

        self._tracer: Tracer = tracer
    #endregion

    #region Get/Add Indicators
    def _add_indicator(self, name, function):
        self._indicators.append(Indicator(name, function))

    def _get_indicator_by_name(self, name):
        for i in self._indicators:
            if i.name == name:
                return i

        return None

    def get_random_indicator_names(self, must: str = None, skip:List = None,  min: int = 3, max: int = 6):



        all_indicator_names = [indikator.name for indikator in self._indicators]

        if skip is not None:
            all_indicator_names = [element for element in all_indicator_names if element not in skip]

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
    #endregion

    #region Predict
    def _predict(self, predict_values, factor=0.7):
        self._tracer.debug(f"Predict for multiple values {predict_values} and factor {factor}")
        if (predict_values.count(TradeAction.BUY) + predict_values.count(TradeAction.BOTH)) >= len(
                predict_values) * factor:
            return TradeAction.BUY
        elif (predict_values.count(TradeAction.SELL) + predict_values.count(TradeAction.BOTH)) >= len(
                predict_values) * factor:
            return TradeAction.SELL

        return TradeAction.NONE

    def predict_some(self, df, indicator_names):
        predict_values = []
        for indicator in self._get_indicators_by_names(indicator_names):
            predict_values.append(indicator.function(df))

        return self._predict(predict_values, 1.0)

    def predict_all(self, df, factor: float = 0.7):
        predict_values = []
        for indicator in self._indicators:
            predict_values.append(indicator.function(df))

        return self._predict(predict_values, factor)
    #endregion

    #region BL
    def _ema_predict(self, df):
        current_ema_10 = df.EMA_10.iloc[-1]
        current_ema_20 = df.EMA_20.iloc[-1]
        current_ema_30 = df.EMA_30.iloc[-1]

        if current_ema_10 > current_ema_20 > current_ema_30:
            return TradeAction.BUY
        elif current_ema_30 > current_ema_20 > current_ema_10:
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

    def _rsi_predict(self, df):
        current_rsi = df.RSI.iloc[-1]
        if current_rsi < 50:
            return TradeAction.SELL
        elif current_rsi > 50:
            return TradeAction.BUY

        return TradeAction.NONE

    def _convergence_predict(self, df, indicator_name):
        pv = PivotScanner()

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

    def _rsi_convergence_predict(self, df):
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

    def _candle_predict(self, df):
        c = Candle(df[-1:])

        if c.direction() == Direction.Bullish:
            return TradeAction.BUY
        else:
            return TradeAction.SELL

    def _macd_predict(self, df):
        current_macd = df.MACD.iloc[-1]
        current_signal = df.SIGNAL.iloc[-1]
        if current_macd > current_signal:
            return TradeAction.BUY
        else:
            return TradeAction.SELL

    def _macd_convergence_predict(self, df):
        return self._convergence_predict(df, "MACD")

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

    def _adx_predict(self, df):
        adx = df.ADX.iloc[-1]

        if adx > 25:
            return TradeAction.BOTH

        return TradeAction.NONE

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

    def _ichimoku_predict(self, df):

        actions = []
        actions.append(self._ichimoku_tenkan_kijun_predict(df))
        actions.append(self._ichimoku_chikou_predict(df))
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
        chikou = df.CHIKOU.iloc[-1]
        close = df.close.iloc[-1]

        if chikou > close:
            return TradeAction.BUY
        else:
            return TradeAction.SELL

    def _ichimoku_cloud_thickness_predict(self, df):
        period = df[-4:]
        cloud_thickness = period.SENKOU_A - period.SENKOU_B

        if cloud_thickness.iloc[-1] > 0:
            if cloud_thickness.iloc[-1] > cloud_thickness[-4:-1].max():
                return TradeAction.BUY
        else:
            if cloud_thickness.iloc[-1] < cloud_thickness[-4:-1].min():
                return TradeAction.SELL

        return TradeAction.NONE
    #endregion
