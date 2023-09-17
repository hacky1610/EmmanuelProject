from BL.candle import Candle, Direction
from Predictors.base_predictor import BasePredictor
import random


class Indicator:
    def __init__(self, name, function):
        self.name = name
        self.function = function


class Indicators:
    _indicators = []
    RSI = "rsi"
    RSI30_70 = "rsi_30_70"
    RSISLOPE = "rsi_slope"
    MACD = "macd"
    MACDCROSSING = "macd_crossing"
    ADX = "adx"
    EMA = "ema"
    PSAR = "psar"
    CCI = "cci"
    CANDLE = "candle"
    BB = "bb"
    ICHIMOKU = "ichi"
    _indicator_confirm_factor = 0.7

    def __init__(self):
        self._add_indicator(self.RSI, self._rsi_confirmation)
        self._add_indicator(self.RSI30_70, self._rsi_smooth_30_70)
        self._add_indicator(self.MACD, self._macd_confirmation)
        self._add_indicator(self.MACDCROSSING, self._macd_crossing_confirmation)
        self._add_indicator(self.ADX, self._adx_confirmation)
        self._add_indicator(self.EMA, self._ema_confirmation)
        self._add_indicator(self.BB, self._bb_confirmation)
        self._add_indicator(self.CANDLE, self._candle_confirmation)
        self._add_indicator(self.CCI, self._cci_confirmation)
        self._add_indicator(self.RSISLOPE, self._rsi_smooth_slope)
        self._add_indicator(self.PSAR, self._psar_confirmation)
        self._add_indicator(self.ICHIMOKU, self._ichimoku_predict)

    def _add_indicator(self, name, function):
        self._indicators.append(Indicator(name, function))

    def _get_indicator_by_name(self, name):
        for i in self._indicators:
            if i.name == name:
                return i

        raise Exception()

    @staticmethod
    def get_random_indicator_names(must):
        all_indicator_names = [Indicators.RSI,
                               Indicators.RSISLOPE,
                               Indicators.MACD,
                               Indicators.MACDCROSSING,
                               Indicators.EMA,
                               Indicators.BB,
                               Indicators.PSAR,
                               Indicators.CCI,
                               Indicators.ICHIMOKU,
                               Indicators.ADX]
        r = random.choices(all_indicator_names, k=random.randint(3,6))
        r.append(must)

        return list(set(r))

    def _get_indicators_by_names(self, names):
        indicators = []
        for n in names:
            indicators.append(self._get_indicator_by_name(n))

        return indicators

    def _predict(self, predict_values, factor=0.7):
        if (predict_values.count(BasePredictor.BUY) + predict_values.count(BasePredictor.BOTH)) >= len(
                predict_values) * factor:
            return BasePredictor.BUY
        elif (predict_values.count(BasePredictor.SELL) + predict_values.count(BasePredictor.BOTH)) >= len(
                predict_values) * factor:
            return BasePredictor.SELL

        return BasePredictor.NONE

    def predict_some(self, df, indicator_names):
        predict_values = []
        for indicator in self._get_indicators_by_names(indicator_names):
            predict_values.append(indicator.function(df))

        return self._predict(predict_values, 1.0)


    def predict_all(self, df, factor:float = 0.7):
        predict_values = []
        for indicator in self._indicators:
            predict_values.append(indicator.function(df))

        return self._predict(predict_values,factor)



    def _ema_confirmation(self, df):
        current_ema_10 = df[-1:].EMA_10.item()
        current_ema_20 = df[-1:].EMA_20.item()
        current_ema_30 = df[-1:].EMA_30.item()

        if current_ema_10 > current_ema_20 > current_ema_30:
            return BasePredictor.BUY
        elif current_ema_30 > current_ema_20 > current_ema_10:
            return BasePredictor.SELL

        return BasePredictor.NONE

    def _rsi_confirmation(self, df):
        current_rsi = df[-1:].RSI.item()
        if current_rsi < 50:
            return BasePredictor.SELL
        elif current_rsi > 50:
            return BasePredictor.BUY

        return BasePredictor.NONE

    def _cci_confirmation(self, df):
        cci = df[-1:].CCI.item()

        if cci > 100:
            return BasePredictor.BUY
        elif cci < -100:
            return BasePredictor.SELL

        return BasePredictor.NONE

    def _psar_confirmation(self, df):
        psar = df[-1:].PSAR.item()
        ema_20 = df[-1:].EMA_20.item()
        close = df[-1:].close.item()

        if psar < ema_20 and close > ema_20 and psar < close:
            return BasePredictor.BUY
        elif psar > ema_20 and close < ema_20 and psar > close:
            return BasePredictor.SELL

        return BasePredictor.NONE

    def _candle_confirmation(self, df):
        c = Candle(df[-1:])

        if c.direction() == Direction.Bullish:
            return BasePredictor.BUY
        else:
            return BasePredictor.SELL

    def _macd_confirmation(self, df):
        current_macd = df[-1:].MACD.item()
        current_signal = df[-1:].SIGNAL.item()
        if current_macd > current_signal:
            return BasePredictor.BUY
        else:
            return BasePredictor.SELL

    def _macd_crossing_confirmation(self, df):
        period = df[-4:-1]
        current_macd = df[-1:].MACD.item()
        current_signal = df[-1:].SIGNAL.item()
        if current_macd > current_signal: #MACD größer als SIGNAL
            if len(period[period.MACD < period.SIGNAL]) > 0:
                return BasePredictor.BUY
        else: #SIGNAL größer als MACD
            if len(period[period.MACD > period.SIGNAL]) > 0:
                return BasePredictor.SELL

    def _bb_confirmation(self, df):
        bb_middle = df[-1:].BB_MIDDLE.item()
        bb_upper = df[-1:].BB_UPPER.item()
        bb_lower = df[-1:].BB_LOWER.item()
        close = df[-1:].close.item()

        if bb_middle < close < bb_upper:
            return BasePredictor.BUY
        elif bb_middle > close > bb_lower:
            return BasePredictor.SELL

        return BasePredictor.NONE

    def _adx_confirmation(self, df):
        adx = df.ADX[-1:].item()

        if adx > 25:
            return BasePredictor.BOTH

        return BasePredictor.NONE

    def _rsi_smooth_slope(self, df):
        diff = df.RSI_SMOOTH.diff()[-1:].item()
        if diff < 0:
            return BasePredictor.SELL
        else:
            return BasePredictor.BUY

    def _rsi_smooth_30_70(self, df):
        rsi_smooth = df.RSI_SMOOTH[-1:].item()
        if rsi_smooth > 70:
            return BasePredictor.BUY
        elif rsi_smooth < 30:
            return BasePredictor.SELL

        return BasePredictor.NONE

    def _ichimoku_predict(self, df):

        actions = []
        actions.append(self._ichimoku_tenkan_kijun_predict(df))
        actions.append(self._ichimoku_chikou_predict(df))
        actions.append(self._ichimoku_cloud_predict(df))

        if actions.count(BasePredictor.BUY) == len(actions):
            return BasePredictor.BUY
        elif actions.count(BasePredictor.SELL) == len(actions):
            return BasePredictor.SELL

        return BasePredictor.NONE



    def _ichimoku_cloud_predict(self, df):
        senkou_a = df.SENKOU_A[-1:].item()
        senkou_b = df.SENKOU_B[-1:].item()
        close = df.close[-1:].item()

        if senkou_a > senkou_b:
            if close > senkou_a:
                return BasePredictor.BUY
        else:
            if close < senkou_a:
                return BasePredictor.SELL

        return BasePredictor.NONE

    def _ichimoku_tenkan_kijun_predict(self, df):
        period = df[-4:-1]
        tenkan = df.TENKAN[-1:].item()
        kijun = df.KIJUN[-1:].item()

        if tenkan > kijun:
            if len(period[period.TENKAN < period.KIJUN]) > 0:
                return BasePredictor.BUY
        else:
            if len(period[period.TENKAN > period.KIJUN]) > 0:
                return BasePredictor.SELL

        return BasePredictor.NONE

    def _ichimoku_chikou_predict(self, df):
        chikou = df.CHIKOU[-1:].item()
        close = df.close[-1:].item()

        if chikou > close:
            return BasePredictor.BUY
        else:
            return BasePredictor.SELL



