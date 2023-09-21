import unittest
from unittest.mock import MagicMock, patch
from BL.high_low_scanner import PivotScanner, ShapeType
import pandas as pd
import numpy as np
from pandas import DataFrame, Series

from Predictors.base_predictor import BasePredictor


class HighLowScannerTest(unittest.TestCase):

    def setUp(self):
        self.scanner = PivotScanner()
        self.df = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=100, freq='D'),
            'open': np.random.rand(100),
            'high': np.random.rand(100),
            'low': np.random.rand(100),
            'close': np.random.rand(100),
            'ATR': np.random.rand(100)
        })

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

    def test_get_pivotid(self):
        # Testing get_pivotid function
        pivot_scanner = PivotScanner()
        df = pd.DataFrame({
            'low': [10, 5, 15, 8, 20],
            'high': [12, 8, 18, 12, 25]
        })

        # Call the function with different values
        self.assertEqual(pivot_scanner.get_pivotid(df, 0, 2, 2), 0)  # No pivot at index 0
        self.assertEqual(pivot_scanner.get_pivotid(df, 1, 2, 2), 0)
        self.assertEqual(pivot_scanner.get_pivotid(df, 2, 2, 2), 0)  # Both pivots at index 2
        self.assertEqual(pivot_scanner.get_pivotid(df, 3, 2, 2), 0)  # Only pivot low at index 3
        self.assertEqual(pivot_scanner.get_pivotid(df, 4, 2, 2), 2)  # Only pivot high at index 4

        self.assertEqual(pivot_scanner.get_pivotid(df, 0, 1, 1), 0)  # No pivot at index 0
        self.assertEqual(pivot_scanner.get_pivotid(df, 1, 1, 1), 1)
        self.assertEqual(pivot_scanner.get_pivotid(df, 2, 1, 1), 2)  # Both pivots at index 2
        self.assertEqual(pivot_scanner.get_pivotid(df, 3, 1, 1), 1)  # Only pivot low at index 3
        self.assertEqual(pivot_scanner.get_pivotid(df, 4, 1, 1), 2)  # Only pivot high at index 4

    def test_pointpos(self):
        # Testing pointpos function
        pivot_scanner = PivotScanner()
        row_pivot_1 = {'pivot_point': 1, 'low': 10, 'high': 20}
        row_pivot_2 = {'pivot_point': 2, 'low': 10, 'high': 20}
        row_no_pivot = {'pivot_point': 0, 'low': 10, 'high': 20}

        # Call the function with different rows
        self.assertAlmostEqual(pivot_scanner.pointpos(row_pivot_1), 9.999)  # 10 - 1e-3
        self.assertAlmostEqual(pivot_scanner.pointpos(row_pivot_2), 20.001)  # 20 + 1e-3
        self.assertTrue(np.isnan(pivot_scanner.pointpos(row_no_pivot)))

    @patch('BL.high_low_scanner.PivotScanner.get_pivotid', side_effect=[3, 1, 2, 0, 3])
    def test_get_pivot_ids(self, mock_get_pivotid):
        # Testing get_pivot_ids function
        pivot_scanner = PivotScanner()
        df = pd.DataFrame({
            'low': [10, 5, 15, 8, 20],
            'high': [12, 8, 18, 12, 25]
        })

        pivot_ids = pivot_scanner.get_pivot_ids(df)

        # Ensure that the get_pivotid is called correctly for each row
        self.assertEqual(mock_get_pivotid.call_args_list, [
            ((df, 0, 3, 3),),
            ((df, 1, 3, 3),),
            ((df, 2, 3, 3),),
            ((df, 3, 3, 3),),
            ((df, 4, 3, 3),),
        ])

        # Ensure that the returned pivot_ids are correct
        self.assertEqual(list(pivot_ids), [3, 1, 2, 0, 3])

    def test_is_ascending_triangle(self):
        # Testing _is_ascending_triangle function
        pivot_scanner = PivotScanner()
        slmin = 0.2
        slmax = 0.3
        xxmax = np.array([19, 5, 10, 15, 20])
        atr = 1.0

        self.assertTrue(pivot_scanner._is_ascending_triangle(slmin, slmax, xxmax, atr))

        pivot_scanner = PivotScanner()
        slmin = -0.2
        slmax = 0.3
        xxmax = np.array([19, 5, 10, 15, 20])
        atr = 1.0

        self.assertFalse(pivot_scanner._is_ascending_triangle(slmin, slmax, xxmax, atr))

        pivot_scanner = PivotScanner()
        slmin = -0.2
        slmax = 0.3
        xxmax = np.array([15, 5, 10, 15, 20])
        atr = 1.0

        self.assertFalse(pivot_scanner._is_ascending_triangle(slmin, slmax, xxmax, atr))

    # Add more unittests for other functions as needed...

