import unittest
from unittest.mock import patch, MagicMock
from pandas import DataFrame
from Connectors.dropbox_cache import DropBoxCache
from Connectors.tiingo import Tiingo
from Tracing.Tracer import Tracer


class TiingoTest(unittest.TestCase):

    def setUp(self):
        conf_reader = MagicMock()
        cache = MagicMock()
        conf_reader.read_config = MagicMock(return_value={"ti_api_key":"key"})
        self.tiingo = Tiingo(conf_reader=conf_reader,cache=cache)

    def test_get_historical_data_no_content(self):
        self.tiingo._send_request = MagicMock(return_value=[])
        res = self.tiingo._send_history_request("Fii", "BAR", "HELLO", "la")
        assert len(res) == 0

    def test_get_historical_data_connection_exception(self):
        self.tiingo._send_request = MagicMock(return_value="")
        res = self.tiingo._send_history_request("Fii", "BAR", "HELLO", "la")
        assert len(res) == 0

    def test_load_data_connection_exception(self):
        self.tiingo._send_request = MagicMock(return_value="")
        res = self.tiingo.load_data_by_date("Foo", "start", "end", None)
        assert len(res) == 0




    @patch.object(Tiingo, '_send_history_request')
    @patch.object(DropBoxCache, 'load_cache')
    def test_data_loaded_from_cache_when_cache_exists_and_use_cache_is_true(self, mock_load_cache,
                                                                       mock_send_history_request):
        mock_load_cache.return_value = DataFrame({"date": ["2022-01-01T00:00:00.000Z"]})
        mock_send_history_request.return_value = DataFrame({"date": ["2022-01-02T00:00:00.000Z"]})

        tiingo = Tiingo(MagicMock(), DropBoxCache(MagicMock()), Tracer())
        df = tiingo.load_data_by_date("ticker", "2021-02-01", None, MagicMock(), use_cache=True, validate=False)
        self.assertFalse(df.empty)

    @patch.object(DropBoxCache, 'load_cache')
    def test_data_loaded_from_cache_when_cache_exists_and_use_cache_is_true_and_end_is_set(self, mock_load_cache):
        mock_load_cache.return_value = DataFrame({"date": ["2022-01-01T00:00:00.000Z", "2024-01-01T00:00:00.000Z"]})

        tiingo = Tiingo(MagicMock(), DropBoxCache(MagicMock()), Tracer())
        df = tiingo.load_data_by_date("ticker", "2021-02-01", "2023-03-01", MagicMock(), use_cache=True, validate=False)
        assert len(df) == 1

    @patch.object(Tiingo, '_send_history_request')
    @patch.object(DropBoxCache, 'load_cache')
    def test_data_loaded_from_request_when_cache_exists_and_use_cache_is_false(self, mock_load_cache,
                                                                          mock_send_history_request):
        mock_load_cache.return_value = DataFrame()
        mock_send_history_request.return_value = DataFrame({"date": ["2022-01-01T00:00:00.000Z"]})

        tiingo = Tiingo(MagicMock(), DropBoxCache(MagicMock()), Tracer())
        df = tiingo.load_data_by_date("ticker", "2021-02-01", None, MagicMock(), use_cache=False, validate=False)
        self.assertFalse(df.empty)

    @patch.object(Tiingo, '_send_history_request')
    @patch.object(DropBoxCache, 'load_cache')
    def test_data_loaded_from_request_when_cache_does_not_exist(self, mock_load_cache, mock_send_history_request):
        mock_load_cache.return_value = DataFrame()
        mock_send_history_request.return_value = DataFrame({"date": ["2022-01-01T00:00:00.000Z"]})

        tiingo = Tiingo(MagicMock(), DropBoxCache(MagicMock()), Tracer())
        df = tiingo.load_data_by_date("ticker", "2021-02-01", None, MagicMock(), use_cache=True, validate=False)
        self.assertFalse(df.empty)

    @patch.object(Tiingo, '_send_history_request')
    @patch.object(DropBoxCache, 'load_cache')
    def test_data_loaded_from_cache_and_request_when_cache_exists_and_end_is_none(self, mock_load_cache,
                                                                             mock_send_history_request):
        mock_load_cache.return_value = DataFrame({"date": ["2022-01-01T00:00:00.000Z"]})
        mock_send_history_request.return_value = DataFrame({"date": ["2022-01-02T00:00:00.000Z"]})

        tiingo = Tiingo(MagicMock(), DropBoxCache(MagicMock()), Tracer())
        df = tiingo.load_data_by_date("ticker", "2021-02-01", None, MagicMock(), use_cache=True, validate=False)
        self.assertEqual(len(df), 2)




