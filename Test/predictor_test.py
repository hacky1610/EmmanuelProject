import unittest
from pandas import Series, DataFrame
from Predictors.old.cci_ema import CCI_EMA
from Predictors.old.rsi_stoch import RsiStoch
from Predictors.old.rsi_bb import RsiBB


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
    def setUp(self):
        self._predictor = RsiStoch()

    def test_df_to_small(self):
        df = DataFrame()
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        df = df.append(Series([50, 50, 50], index=["RSI", "STOCHD", "STOCHK"]), ignore_index=True)
        res = self._predictor.predict(df)
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
        res = self._predictor.predict(df)
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
        res = self._predictor.predict(df)
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
        res = self._predictor.predict(df)
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


class RsiBBTest(unittest.TestCase):
    def setUp(self):
        self._predictor = RsiBB()

    def add_line(self, df: DataFrame, low, high, rsi, bb_lower, bb_middle,bb_upper):
        return df.append(
            Series([low, high, rsi, bb_lower,bb_middle, bb_upper,"date"],
                   index=["low", "high", "RSI", "BB_LOWER","BB_MIDDLE" , "BB_UPPER", "date"]),
            ignore_index=True)

    def test_df_to_small(self):
        df = DataFrame()
        df = self.add_line(df, 900, 901, 50, 800, 900, 1000)
        df = self.add_line(df, 900, 901, 50, 800, 900, 1000)
        res = self._predictor.predict(df)
        assert res == "none"

    def test_df_no_peek(self):
        df = DataFrame()
        df = self.add_line(df, 900, 901, 50, 800,900, 1000)
        df = self.add_line(df, 900, 901, 50, 800,900, 1000)
        df = self.add_line(df, 900, 901, 50, 800,900, 1000)
        df = self.add_line(df, 900, 901, 50, 800,900, 1000)
        df = self.add_line(df, 900, 901, 50, 800,900, 1000)
        df = self.add_line(df, 900, 901, 50, 800,900, 1000)
        df = self.add_line(df, 900, 901, 50, 800,900, 1000)
        df = self.add_line(df, 900, 901, 50, 800,900, 1000)
        res = self._predictor.predict(df)
        assert res == "none"

    def test_buy(self):
        df = DataFrame()
        df = self.add_line(df, 900, 901, 50, 800,900, 1000)
        df = self.add_line(df, 900, 901, 50, 800,900, 1000)
        df = self.add_line(df, 900, 901, 50, 800,900, 1000)
        df = self.add_line(df, 900, 901, 50, 800,900, 1000)
        df = self.add_line(df, 900, 901, 50, 800,1050, 1000)
        df = self.add_line(df, 900, 901, 50, 800,1000, 1000)
        df = self.add_line(df, 900, 901, 50, 800,950, 1000)
        df = self.add_line(df, 700, 901, 20, 800,900, 1000)
        res = self._predictor.predict(df)
        assert res == "buy"

    def test_sell(self):
        df = DataFrame()
        df = self.add_line(df, 900, 901, 50, 800,900, 1000)
        df = self.add_line(df, 900, 901, 50, 800,900, 1000)
        df = self.add_line(df, 900, 901, 50, 800,900, 1000)
        df = self.add_line(df, 900, 901, 50, 800,900, 1000)
        df = self.add_line(df, 900, 901, 50, 800,750, 1000)
        df = self.add_line(df, 900, 901, 50, 800,500, 1000)
        df = self.add_line(df, 900, 901, 50, 800,850, 1000)
        df = self.add_line(df, 900, 1001, 81, 800,900, 1000)
        res = self._predictor.predict(df)
        assert res == "sell"

    def test_none_peek_to_far_away(self):
        df = DataFrame()
        df = self.add_line(df, 900, 1001, 81, 800,900, 1000)
        df = self.add_line(df, 900, 901, 50, 800,900, 1000)
        df = self.add_line(df, 900, 901, 50, 800,900, 1000)
        df = self.add_line(df, 900, 901, 50, 800,900, 1000)
        df = self.add_line(df, 900, 901, 50, 800,900, 1000)
        df = self.add_line(df, 900, 901, 50, 800,900, 1000)
        df = self.add_line(df, 900, 901, 50, 800,900, 1000)
        df = self.add_line(df, 900, 901, 50, 800,900, 1000)
        res = self._predictor.predict(df)
        assert res == "none"
