import unittest
from unittest.mock import MagicMock
from BL.analytics import Analytics
from BL.high_low_scanner import PivotScanner
from Predictors.base_predictor import BasePredictor
from pandas import DataFrame, Series


class HighLowScannerTest(unittest.TestCase):

    def setUp(self):
        self.scanner = PivotScanner()

    def add_line(self, df: DataFrame, high, low):
        return df.append(
            Series([ high, low],
                   index=["high", "low" ]),
            ignore_index=True)



    def test_no_high_no_low(self):

        df = DataFrame()
        df = self.add_line(df, 10,10)
        df = self.add_line(df, 10, 10)
        df = self.add_line(df, 10, 10)
        df = self.add_line(df, 10, 10)
        df = self.add_line(df, 10, 10)
        df = self.add_line(df, 10, 10)
        df = self.add_line(df, 10, 10)
        df = self.add_line(df, 10, 10)
        df = self.add_line(df, 10, 10)
        df = self.add_line(df, 10, 10)
        df = self.add_line(df, 10, 10)
        df = self.add_line(df, 10, 10)



        res = self.scanner.get_pivot_ids(df)
        print(res)

