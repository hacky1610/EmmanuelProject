from BL.datatypes import TradeAction
from Predictors.base_predictor import BasePredictor
import numpy as np

class IndicatorBL:
    @staticmethod
    def is_crossing(a, b):
        print((a - b).max() > 0 > (a - b).min())

    @staticmethod
    def get_trend(column, step=1):
        diff = column.diff(step)
        mean = (abs(diff)).mean()
        if diff[-1:].item() > mean:
            return 1
        elif diff[-1:].item() > mean * -1:
            return -1

        return 0

    @staticmethod
    def interpret_candle(candle):
        open = candle.open.item()
        close = candle.close.item()
        if close > open:
            # if (high - low) * percentage < close - open:
            return TradeAction.BUY
        elif close < open:
            # if (high - low) * percentage < open - close:
            return TradeAction.SELL

        return TradeAction.NONE

    @staticmethod
    def check_macd_divergence(df):
        # Berechne den MACD-Indikator und das Signal
        # Extrahiere die MACD-Linie und das Signal

        macd_line = df.MACD.values
        signal_line = df.SIGNAL.values

        # Überprüfe, ob in den letzten 10 Zeiteinheiten eine Divergenz aufgetreten ist
        last_macd_line = macd_line[-10:]
        last_signal_line = signal_line[-10:]
        last_price = df['close'][-10:].values
        last_lowest_macd_line = np.argmin(last_macd_line)
        last_highest_macd_line = np.argmax(last_macd_line)
        last_lowest_price = np.argmin(last_price)
        last_highest_price = np.argmax(last_price)
        if last_lowest_macd_line < last_lowest_price:
            return 1
        elif last_highest_macd_line > last_highest_price:
            return -1
        else:
            return 0

    @staticmethod
    def check_rsi_divergence(df, step: int = 5):
        # Berechne den MACD-Indikator und das Signal
        # Extrahiere die MACD-Linie und das Signal

        rsi_line = df.RSI.values

        # Überprüfe, ob in den letzten 10 Zeiteinheiten eine Divergenz aufgetreten ist
        last_macd_line = rsi_line[step * -1:]
        last_price = df['close'][step * -1:].values
        last_lowest_macd_line = np.argmin(last_macd_line)
        last_highest_macd_line = np.argmax(last_macd_line)
        last_lowest_price = np.argmin(last_price)
        last_highest_price = np.argmax(last_price)
        if last_lowest_macd_line < last_lowest_price:
            return 1
        elif last_highest_macd_line > last_highest_price:
            return -1
        else:
            return 0

    @staticmethod
    def predict_ema_3(df, period: int = 2):
        period = df[period * -1:]

        ema_14_over_25 = len(period[period.EMA_14 > period.EMA_25]) == len(period)
        ema_25_over_50 = len(period[period.EMA_25 > period.EMA_50]) == len(period)

        ema_14_under_25 = len(period[period.EMA_14 < period.EMA_25]) == len(period)
        ema_25_under_50 = len(period[period.EMA_25 < period.EMA_50]) == len(period)

        if ema_14_over_25 and ema_25_over_50:
            return TradeAction.BUY

        if ema_14_under_25 and ema_25_under_50:
            return TradeAction.SELL

        return TradeAction.NONE

    @staticmethod
    def calc_trend(df, period: int = 2):
        period = df[period * -1:]

        ema_14_over_25 = len(period[period.EMA_14 > period.EMA_25]) == len(period)
        ema_25_over_50 = len(period[period.EMA_25 > period.EMA_50]) == len(period)

        ema_14_under_25 = len(period[period.EMA_14 < period.EMA_25]) == len(period)
        ema_25_under_50 = len(period[period.EMA_25 < period.EMA_50]) == len(period)

        if ema_14_over_25 and ema_25_over_50:
            return 1

        if ema_14_under_25 and ema_25_under_50:
            return -1

        return 0

    @staticmethod
    def predict_macd(df, period: int = 2, consider_gradient: bool = False):
        current_macd_periode = df[period * -1:]
        macd_over_signal = len(current_macd_periode[current_macd_periode.MACD > current_macd_periode.SIGNAL]) == len(
            current_macd_periode)
        macd_under_signal = len(current_macd_periode[current_macd_periode.MACD < current_macd_periode.SIGNAL]) == len(
            current_macd_periode)

        cur_macd = df[-1:].MACD.item()
        cur_sig = df[-1:].SIGNAL.item()
        pre_macd = df[-2:-1].MACD.item()
        pre_sig = df[-2:-1].SIGNAL.item()

        if macd_over_signal:
            if consider_gradient:
                if cur_macd - cur_sig > pre_macd - pre_sig:
                    return TradeAction.BUY
                else:
                    return TradeAction.NONE

            return TradeAction.BUY

        if macd_under_signal:
            if consider_gradient:
                if cur_sig - cur_macd > pre_sig - pre_macd:
                    return TradeAction.SELL
                else:
                    return TradeAction.NONE

            return TradeAction.SELL

        return TradeAction.NONE

    @staticmethod
    def predict_bb_1(df, period: int = 2):
        current_bb_periode = df[period * -1:]
        low_over = len(current_bb_periode[current_bb_periode.low > current_bb_periode.BB1_UPPER]) == len(
            current_bb_periode)
        high_under = len(current_bb_periode[current_bb_periode.high < current_bb_periode.BB_LOWER]) == len(
            current_bb_periode)

        if low_over:
            return TradeAction.BUY

        if high_under:
            return TradeAction.SELL

        return TradeAction.NONE
