import unittest
from pandas import Series, DataFrame
from Predictors.cci_ema import CCI_EMA
from Predictors.rsi_stoch import RsiStoch


class PredictorTest(unittest.TestCase):

    def test_set_config_default(self):
        pred = CCI_EMA({})
        pred.set_config("Foo")
        assert pred.upper_limit == 90

    def test_set_config_GBPUSD(self):
        pred = CCI_EMA({})
        pred.set_config("GBPUSD")
        assert pred.upper_limit == 90


class RsiStochTest(unittest.TestCase):
    def test_df_to_small(self):
        pred = RsiStoch({})
        df = DataFrame()
        df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        res = pred.predict(df)
        assert res == "none"

    def test_df_no_peek(self):
        pred = RsiStoch({})
        df = DataFrame()
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        res = pred.predict(df)
        assert res == "none"

    def test_buy(self):
        pred = RsiStoch({})
        df = DataFrame()
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 10, 10], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 10, 10], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([10, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        res = pred.predict(df)
        assert res == "buy"

    def test_sell(self):
        pred = RsiStoch({})
        df = DataFrame()
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 90, 90], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 90, 90], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([90, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        res = pred.predict(df)
        assert res == "sell"

    def test_none_peek_to_far_away(self):
        pred = RsiStoch({})
        df = DataFrame()
        df = df.append(Series([50, 10, 10], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 10, 10], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([10, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        res = pred.predict(df)
        assert res == "none"
