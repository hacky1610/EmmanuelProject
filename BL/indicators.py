from BL.candle import Candle, Direction
from Predictors.base_predictor import BasePredictor


class Indicator:
    def __init__(self, name, function):
        self.name = name
        self.function = function


class Indicators:
    _indicators = []
    RSI = "rsi"
    RSISLOPE = "rsi_slope"
    MACD = "macd"
    ADX = "adx"
    EMA = "ema"
    PSAR = "psar"
    CCI = "cci"
    CANDLE = "candle"
    BB = "bb"
    _indicator_confirm_factor = 0.7

    def __init__(self):
        self._add_indicator(self.RSI, self._rsi_confirmation)
        self._add_indicator(self.MACD, self._macd_confirmation)
        self._add_indicator(self.ADX, self._adx_confirmation)
        self._add_indicator(self.EMA, self._ema_confirmation)
        self._add_indicator(self.BB, self._bb_confirmation)
        self._add_indicator(self.CANDLE, self._candle_confirmation)
        self._add_indicator(self.CCI, self._cci_confirmation)
        self._add_indicator(self.RSISLOPE, self._rsi_smooth_slope)
        self._add_indicator(self.PSAR, self._psar_confirmation)

    def _add_indicator(self, name, function):
        self._indicators.append(Indicator(name, function))

    def predict_all(self, df, factor:float = 0.7):
        confirmation_list = []
        for indicator in self._indicators:
            confirmation_list.append(indicator.function(df))

        if (confirmation_list.count(BasePredictor.BUY) + confirmation_list.count(BasePredictor.BOTH)) > len(
                confirmation_list) * factor:
            return BasePredictor.BUY
        elif (confirmation_list.count(BasePredictor.SELL) + confirmation_list.count(BasePredictor.BOTH)) > len(
                confirmation_list) * factor:
            return BasePredictor.SELL

        return BasePredictor.NONE

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
