import unittest
from unittest.mock import MagicMock
from Connectors.tiingo import Tiingo


class TiingoTest(unittest.TestCase):

    def setUp(self):
        self.tiingo = Tiingo()

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
