import unittest
from Tuning.RayTune import RayTune
from Envs.forexEnv import ForexEnv
from Tracing.ConsoleTracer import ConsoleTracer
from unittest.mock import MagicMock
from Connectors.tiingo import Tiingo


class TiingoTest(unittest.TestCase):

    def setUp(self):
        self.tiingo = Tiingo()

    def test_get_historical_data_no_content(self):
        self.tiingo._send_request = MagicMock(return_value=[])
        res = self.tiingo._send_history_request("Fii","BAR","HELLO","la")
        assert res == None
