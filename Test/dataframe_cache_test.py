import unittest
from unittest.mock import  MagicMock

import pandas as pd
from pandas import DataFrame

from BL.indicators import Indicators
from Connectors.dataframe_cache import FourHourDataFrameCache


class DataFrameCacheTest(unittest.TestCase):

    def setUp(self):

        self.dp = MagicMock()

        self.indicators = Indicators(dp=self.dp)

        data = {
            'date': ['2023-08-05 00:00:00', '2023-08-05 01:00:00', '2023-08-05 02:00:00', '2023-08-05 03:00:00',
                     '2023-08-05 04:00:00', '2023-08-05 05:00:00', '2023-08-05 06:00:00', '2023-08-05 07:00:00',
                     '2023-08-05 08:00:00', '2023-08-05 09:00:00', '2023-08-05 10:00:00', '2023-08-05 11:00:00',
                     '2023-08-05 12:00:00', '2023-08-05 13:00:00', '2023-08-05 14:00:00', '2023-08-05 15:00:00',
                     ],
            'open': [7, 2, 3, 4, 5, 6, 7, 8,7, 2, 3, 4, 5, 6, 7, 0],
            'high': [1, 2, 3, 4, 5, 6, 7, 8,7, 2, 3, 4, 5, 6, 7, 0],
            'low': [1, 2, 3, 4, 5, 1, 7, 8,7, 2, 3, 4, 5, 6, 7, 100],
            'close': [1, 2, 3, 4, 5, 6, 7, 8,7, 2, 3, 4, 5, 6, 7, 100]
        }
        self.one_h_df = DataFrame(data)

        self.cache = FourHourDataFrameCache(dataprocessor=self.dp)


    def test_foo(self):

        #Test 1
        test_df = self.one_h_df[:-2]

        result_old = self.indicators.convert_1h_to_4h(test_df)
        result_new = self.cache.get_4h_df(test_df)

        assert result_old.equals(result_new)

        result_old = self.indicators.convert_1h_to_4h(test_df)
        result_new = self.cache.get_4h_df(test_df)

        assert result_old.equals(result_new)

        #Test 2
        test_df = self.one_h_df[:-4]
        result_old = self.indicators.convert_1h_to_4h(test_df)
        result_new = self.cache.get_4h_df(test_df)

        assert result_old.equals(result_new)

        result_old = self.indicators.convert_1h_to_4h(test_df)
        result_new = self.cache.get_4h_df(test_df)

        assert result_old.equals(result_new)

        #Test 2
        test_df = self.one_h_df
        result_old = self.indicators.convert_1h_to_4h(test_df)
        result_new = self.cache.get_4h_df(test_df)

        assert result_old.equals(result_new)

        test_df = self.one_h_df[:-5]
        result_old = self.indicators.convert_1h_to_4h(test_df)
        result_new = self.cache.get_4h_df(test_df)

        assert result_old.equals(result_new)


    def test_aggregation(self):
        data = {
            'date': ['2023-08-05 00:00:00', '2023-08-05 01:00:00', '2023-08-05 02:00:00', '2023-08-05 03:00:00',
                     '2023-08-05 04:00:00', '2023-08-05 05:00:00', '2023-08-05 06:00:00', '2023-08-05 07:00:00'],
            'open': [7, 2, 3, 4, 5, 6, 7, 8],
            'high': [1, 2, 3, 4, 5, 6, 7, 8],
            'low': [1, 2, 3, 4, 5, 1, 7, 8],
            'close': [1, 2, 3, 4, 5, 6, 7, 8]
        }
        one_h_df = DataFrame(data)
        result = self.cache.get_4h_df(one_h_df)

        expected_data = {
            'open': [7, 5],
            'low': [1, 1],
            'high': [4, 8],
            'close': [4, 8]
        }
        expected_df = DataFrame(expected_data)
        pd.testing.assert_frame_equal(result.reset_index(drop=True), expected_df.reset_index(drop=True))




