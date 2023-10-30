import unittest
from datetime import datetime
from pandas import DataFrame
from unittest.mock import MagicMock, patch

from BL.position import Position
from BL.zulu_trader import ZuluTrader
from Connectors.deal_store import Deal
from Connectors.tiingo import TradeType
from Connectors.zulu_api import ZuluApi
from Tracing.Tracer import Tracer

class TestZuluTrader(unittest.TestCase):

    def setUp(self):
        self.deal_storage = MagicMock()
        self.zulu_api = MagicMock()
        self.ig = MagicMock()
        self.trader_store = MagicMock()
        self.tracer = MagicMock()
        self.trader = ZuluTrader(self.deal_storage, self.zulu_api, self.ig, self.trader_store, self.tracer)

    def test_is_still_open(self):
        # Mock-Daten für get_opened_positions
        open_positions = [Position("1", "AAPL", "Buy", datetime(2023, 10, 29, 12, 0))]
        self.zulu_api.get_opened_positions.return_value = open_positions

        result = self.trader._is_still_open("trader_id", "1")

        self.assertTrue(result)

    def test_close_open_positions(self):
        # Mock-Daten für get_open_deals und close
        open_deal = {"trader_id": "trader_id", "id": "1", "epic": "AAPL", "direction": "Buy", "deal_id": "deal_id"}
        self.deal_storage.get_open_deals.return_value = [open_deal]
        self.ig.close.return_value = (True, None)

        self.trader._close_open_positions()

        self.tracer.write.assert_called_with("Close positions")
        self.tracer.write.assert_called_with("Position closed")
        self.deal_storage.update_state.assert_called_with("1", "Closed")

    def test_get_market_by_ticker(self):
        # Mock-Daten für get_markets
        markets = DataFrame({"symbol": ["AAPL", "GOOGL"], "epic": ["AAPL_EPIC", "GOOGL_EPIC"], "currency": ["USD", "USD"]})
        self.ig.get_markets.return_value = markets

        result = self.trader._get_market_by_ticker_or_none(markets, "AAPL")

        self.assertEqual(result["symbol"], "AAPL")
        self.assertEqual(result["epic"], "AAPL_EPIC")
        self.assertEqual(result["currency"], "USD")

    def test_open_new_positions(self):
        # Mock-Daten für _get_positions und _trade_position
        positions = [Position("1", "AAPL", "Buy", datetime(2023, 10, 29, 12, 0))]
        self.trader._get_positions.return_value = positions
        self.trader._trade_position = MagicMock()

        self.trader._open_new_positions()

        self.tracer.write.assert_called_with("Open positions")
        self.trader._trade_position.assert_called_with(markets, positions[0])

    def test_trade_position(self):
        # Mock-Daten für _deal_storage, _ig, _get_market_by_ticker und _zulu_api
        markets = DataFrame({"symbol": ["AAPL", "GOOGL"], "epic": ["AAPL_EPIC", "GOOGL_EPIC"], "currency": ["USD", "USD"]})
        p = Position("1", "AAPL", "Buy", datetime(2023, 10, 29, 12, 0))
        self.trader._get_market_by_ticker_or_none.return_value = markets
        self.ig.open.return_value = (True, {"dealReference": "12345", "dealId": "67890"})
        self.deal_storage.has_id.return_value = False

        self.trader._trade_position(markets, p)

        self.tracer.write.assert_called_with(f"Try to open position {p}")
        self.ig.open.assert_called_with(epic="AAPL_EPIC", direction="Buy", currency="USD")
        self.deal_storage.save.assert_called_with(Deal(zulu_id="1", ticker="AAPL", dealReference="12345", dealId="67890", trader_id="trader_id", epic="AAPL_EPIC", direction="Buy"))

    def test_get_positions(self):
        # Mock-Daten für _trader_store und _zulu_api
        self.trader_store.get_all_trades_df.return_value = DataFrame({"id": ["trader_id"], "name": ["Trader Name"]})
        self.zulu_api.get_opened_positions.return_value = [Position("1", "AAPL", "Buy", datetime(2023, 10, 29, 12, 0))]

        result = self.trader._get_positions()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].get_id(), "1")
        self.assertEqual(result[0].get_ticker(), "AAPL")
        self.assertEqual(result[0].get_direction(), "Buy")

if __name__ == '__main__':
    unittest.main()
