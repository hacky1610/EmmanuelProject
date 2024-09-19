import unittest
from unittest.mock import patch, MagicMock
from pandas import DataFrame

from BL.indicators import Indicators
from Connectors.dropbox_cache import DropBoxCache
from Connectors.tiingo import Tiingo, FourHourDataFrameCache
from Tracing.Tracer import Tracer


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

        self.cache = FourHourDataFrameCache(dataprocessor=self.dp, ohlc_1h_df=self.one_h_df)


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




