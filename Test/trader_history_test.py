import unittest
from unittest.mock import MagicMock
from BL.trader_history import TraderHistory


class TraderHistoryTest(unittest.TestCase):

    def setUp(self):
        pass

    def test_empty_list(self):
        hist = []
        th = TraderHistory(hist)
        th.get_avg_trades_per_week()
        th.get_wl_ratio()
        th.amount_of_peaks()
        th.trader_performance("fsdf")
        assert not th.has_history()

