import unittest
from unittest.mock import  MagicMock

import pandas as pd
from pandas import DataFrame

from BL.indicators import Indicators
from Connectors.dataframe_cache import DataFrameCache


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

        data = {
            'date': pd.date_range('2023-08-05', periods=100, freq='H').strftime('%Y-%m-%d %H:%M:%S').tolist(),
            'open': [i % 10 for i in range(100)],
            'high': [i % 10 + 1 for i in range(100)],
            'low': [i % 10 - 1 for i in range(100)],
            'close': [i % 10 for i in range(100)],
        }
        self.one_h_df_big = DataFrame(data)

        self.cache = DataFrameCache(dataprocessor=self.dp)


    def test_foo(self):

        #Test 1
        self.cache._build_cache_4h(self.one_h_df)

        test_df = self.one_h_df[:-2]

        result_old = self.cache._convert_1h_to_4h(test_df)
        result_new = self.cache.get_4h_df(test_df)

        assert result_old.equals(result_new)

        result_old = self.cache._convert_1h_to_4h(test_df)
        result_new = self.cache.get_4h_df(test_df)

        assert result_old.equals(result_new)

        #Test 2
        test_df = self.one_h_df[:-4]
        result_old = self.cache._convert_1h_to_4h(test_df)
        result_new = self.cache.get_4h_df(test_df)

        assert result_old.equals(result_new)

        result_old = self.cache._convert_1h_to_4h(test_df)
        result_new = self.cache.get_4h_df(test_df)

        assert result_old.equals(result_new)

        #Test 2
        test_df = self.one_h_df
        result_old = self.cache._convert_1h_to_4h(test_df)
        result_new = self.cache.get_4h_df(test_df)

        assert result_old.equals(result_new)

        test_df = self.one_h_df[:-5]
        result_old = self.cache._convert_1h_to_4h(test_df)
        result_new = self.cache.get_4h_df(test_df)

        assert result_old.equals(result_new)

        test_df = self.one_h_df[:-7]
        result_old = self.cache._convert_1h_to_4h(test_df)
        result_new = self.cache.get_4h_df(test_df)

        assert result_old.equals(result_new)

    def test_foo_12(self):

        #Test 1
        self.cache.init_caches(self.one_h_df)

        test_df = self.one_h_df[:-2]

        result_old = self.cache._convert_1h_to_12h(test_df)
        result_new = self.cache.get_12h_df(test_df)

        assert result_old.equals(result_new)

        result_old = self.cache._convert_1h_to_12h(test_df)
        result_new = self.cache.get_12h_df(test_df)

        assert result_old.equals(result_new)

        #Test 2
        test_df = self.one_h_df[:-4]
        result_old = self.cache._convert_1h_to_12h(test_df)
        result_new = self.cache.get_12h_df(test_df)

        assert result_old.equals(result_new)

        result_old = self.cache._convert_1h_to_12h(test_df)
        result_new = self.cache.get_12h_df(test_df)

        assert result_old.equals(result_new)

        #Test 2
        test_df = self.one_h_df
        result_old = self.cache._convert_1h_to_12h(test_df)
        result_new = self.cache.get_12h_df(test_df)

        assert result_old.equals(result_new)

        test_df = self.one_h_df[:-5]
        result_old = self.cache._convert_1h_to_12h(test_df)
        result_new = self.cache.get_12h_df(test_df)

        assert result_old.equals(result_new)

        test_df = self.one_h_df[:-7]
        result_old = self.cache._convert_1h_to_12h(test_df)
        result_new = self.cache.get_12h_df(test_df)

        assert result_old.equals(result_new)

    def test_foo_24(self):

        #Test 1
        self.cache.init_caches(self.one_h_df)

        test_df = self.one_h_df[:-2]

        result_old = self.cache._convert_1h_to_24h(test_df)
        result_new = self.cache.get_1d_df(test_df)

        assert result_old.equals(result_new)

        result_old = self.cache._convert_1h_to_24h(test_df)
        result_new = self.cache.get_1d_df(test_df)

        assert result_old.equals(result_new)

        #Test 2
        test_df = self.one_h_df[:-4]
        result_old = self.cache._convert_1h_to_24h(test_df)
        result_new = self.cache.get_1d_df(test_df)

        assert result_old.equals(result_new)

        result_old = self.cache._convert_1h_to_24h(test_df)
        result_new = self.cache.get_1d_df(test_df)

        assert result_old.equals(result_new)

        #Test 2
        test_df = self.one_h_df
        result_old = self.cache._convert_1h_to_24h(test_df)
        result_new = self.cache.get_1d_df(test_df)

        assert result_old.equals(result_new)

        test_df = self.one_h_df[:-5]
        result_old = self.cache._convert_1h_to_24h(test_df)
        result_new = self.cache.get_1d_df(test_df)

        assert result_old.equals(result_new)

        test_df = self.one_h_df[:-7]
        result_old = self.cache._convert_1h_to_24h(test_df)
        result_new = self.cache.get_1d_df(test_df)

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
        self.cache._build_cache_4h(one_h_df)
        result = self.cache.get_4h_df(one_h_df)

        expected_data = {
            'open': [7, 5],
            'high': [4, 8],
            'low': [1, 1],
            'close': [4, 8]
        }
        expected_df = DataFrame(expected_data)
        pd.testing.assert_frame_equal(result.reset_index(drop=True), expected_df.reset_index(drop=True))

    def test_aggregation_100h_4h(self):
        # Test aggregation on a 100-hour DataFrame
        self.cache.init_caches(self.one_h_df_big)
        result = self.cache.get_4h_df(self.one_h_df_big)

        # Check if the aggregated DataFrame has the expected number of rows (1 row per 4 hours)
        expected_rows = len(self.one_h_df_big) // 4
        self.assertEqual(len(result), expected_rows)

        self.assertEqual(result.iloc[-1].close, 9)
        self.assertEqual(result.iloc[-1].low, 5)

        result = self.cache.get_4h_df(self.one_h_df_big[:-15])
        self.assertEqual(result.iloc[-1].close, 4)
        self.assertEqual(result.iloc[-1].open, 1)

        result = self.cache.get_4h_df(self.one_h_df_big[:-33])
        self.assertEqual(result.iloc[-1].close, 6)
        self.assertEqual(result.iloc[-1].high, 7)

    def test_aggregation_100h_12h(self):
        # Test aggregation on a 100-hour DataFrame
        self.cache.init_caches(self.one_h_df_big)
        result = self.cache.get_12h_df(self.one_h_df_big)

        # Check if the aggregated DataFrame has the expected number of rows (1 row per 4 hours)
        #self.assertEqual(len(result), 8)

        #return

        self.assertEqual(result.iloc[-1].close, 9)
        self.assertEqual(result.iloc[-1].low, -1)

        result = self.cache.get_12h_df(self.one_h_df_big[:-15])
        self.assertEqual(result.iloc[-1].close, 4)
        self.assertEqual(result.iloc[-1].high, 10)

    def test_aggregation_100h_24h(self):
        # Test aggregation on a 100-hour DataFrame
        self.cache.init_caches(self.one_h_df_big)
        result = self.cache.get_1d_df(self.one_h_df_big)

        # Check if the aggregated DataFrame has the expected number of rows (1 row per 4 hours)
        # self.assertEqual(len(result), 8)

        # return

        self.assertEqual(result.iloc[-1].close, 9)
        self.assertEqual(result.iloc[-1].low, -1)
        self.assertEqual(result.iloc[-1].open, 6)

        result = self.cache.get_1d_df(self.one_h_df_big[:-15])
        self.assertEqual(result.iloc[-1].close, 4)
        self.assertEqual(result.iloc[-1].high, 10)

        result = self.cache.get_1d_df(self.one_h_df_big[:-52])
        self.assertEqual(result.iloc[-1].close, 7)
        self.assertEqual(result.iloc[-1].high, 10)




    def test_aggregation_2(self):
        data = {
            'date': ['2023-08-05 02:00:00', '2023-08-05 03:00:00', '2023-08-05 04:00:00', '2023-08-05 05:00:00',
                     '2023-08-05 06:00:00', '2023-08-05 07:00:00', '2023-08-05 08:00:00', '2023-08-05 09:00:00'],
            'open': [7, 2, 3, 4, 5, 6, 7, 8],
            'high': [1, 2, 3, 4, 5, 6, 7, 8],
            'low': [1, 2, 3, 4, 5, 1, 7, 8],
            'close': [1, 2, 3, 4, 5, 6, 7, 8]
        }
        one_h_df = DataFrame(data)
        self.cache._build_cache_4h(one_h_df)
        result = self.cache.get_4h_df(one_h_df)

        expected_data = {
            'open': [7, 5],
            'high': [4, 8],
            'low': [1, 1],
            'close': [4, 8]
        }
        expected_df = DataFrame(expected_data)
        pd.testing.assert_frame_equal(result.reset_index(drop=True), expected_df.reset_index(drop=True))

    def test_aggregation_3(self):
        data = {
            'date': ['2023-08-05 01:00:00','2023-08-05 02:00:00', '2023-08-05 03:00:00', '2023-08-05 04:00:00', '2023-08-05 05:00:00',
                     '2023-08-05 06:00:00', '2023-08-05 07:00:00', '2023-08-05 08:00:00', '2023-08-05 09:00:00'],
            'open': [1,7, 2, 3, 4, 5, 6, 7, 8],
            'high': [1,1, 2, 3, 4, 5, 6, 7, 8],
            'low': [1,1, 2, 3, 4, 5, 1, 7, 8],
            'close': [1,1, 2, 3, 4, 5, 6, 7, 8]
        }
        one_h_df = DataFrame(data)
        self.cache._build_cache_4h(one_h_df)
        result = self.cache.get_4h_df(one_h_df)

        expected_data = {
            'open': [1,7, 5],
            'high': [1,4, 8],
            'low': [1,1, 1],
            'close': [1,4, 8]
        }
        expected_df = DataFrame(expected_data)
        pd.testing.assert_frame_equal(result.reset_index(drop=True), expected_df.reset_index(drop=True))



