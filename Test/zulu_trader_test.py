import unittest
from datetime import datetime
from pandas import DataFrame, Series
from unittest.mock import MagicMock, patch

from BL.position import Position
from Connectors.trader_store import Trader
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
        self.zulu_ui = MagicMock()
        self.trader = ZuluTrader(deal_storage=self.deal_storage,
                                 zulu_api=self.zulu_api,
                                 ig=self.ig,
                                 trader_store=self.trader_store,
                                 tracer=self.tracer,
                                 zulu_ui=self.zulu_ui)


    def test_close_open_positions_pos_is_still_open(self):
        # Mock-Daten für get_open_deals und close
        open_deal = Deal(zulu_id="zID",dealReference="df", trader_id="tid",dealId="did",
                         direction="SELL", status="open", ticker="AAPL", epic="AAPL.de")
        df = DataFrame()
        df = df.append(Series(data=["zID"], index=["position_id"]), ignore_index=True)

        self.deal_storage.get_open_deals.return_value = [open_deal]
        self.zulu_ui.get_my_open_positions.return_value = df

        self.trader._close_open_positions()

        self.ig.close.assert_not_called()

    def test_close_open_positions_pos_is_closed(self):
        # Mock-Daten für get_open_deals und close
        open_deal = Deal(zulu_id="zID",dealReference="df", trader_id="tid",dealId="did",
                         direction="SELL", status="open", ticker="AAPL", epic="AAPL.de")
        df = DataFrame()

        self.deal_storage.get_open_deals.return_value = [open_deal]
        self.zulu_ui.get_my_open_positions.return_value = df
        self.ig.close.return_value = (True, None)

        self.trader._close_open_positions()

        self.ig.close.assert_called()


    def test_get_market_by_ticker_market_exist(self):
        # Mock-Daten für get_markets
        markets = [{"symbol": "AAPL",
                    "epic": "AAPL_EPIC",
                    "currency": "USD"},
                   {"symbol": "GOO",
                    "epic": "GOO_EPIC",
                    "currency": "USD"},
                   ]
        self.ig.get_markets.return_value = markets

        result = self.trader._get_market_by_ticker_or_none(markets, "AAPL")

        self.assertEqual(result["symbol"], "AAPL")
        self.assertEqual(result["epic"], "AAPL_EPIC")
        self.assertEqual(result["currency"], "USD")

    def test_get_positions_no_good_posttions(self):
        # Mock-Daten für _get_positions und _trade_position
        df = DataFrame()
        df = df.append(Series(data=["1", "foo"],
                              index=["id", "trader_name"]), ignore_index=True)
        self.trader._get_newest_positions = MagicMock(return_value=df)
        self.trader_store.get_trader_by_name.return_value = Trader(id="id",name="name")
        self.zulu_ui.get_my_open_positions.return_value = df

        positions = self.trader._get_positions()
        assert len(positions) == 0

    def test_get_positions_one_good_position(self):
        # Mock-Daten für _get_positions und _trade_position
        df = DataFrame()
        df = df.append(Series(data=["1", "foo"],
                              index=["id", "trader_name"]), ignore_index=True)
        self.trader._get_newest_positions = MagicMock(return_value=df)
        trader = Trader(id="id", name="name")
        trader.hist = MagicMock()
        trader.hist.get_wl_ratio.return_value = 1.0
        self.trader_store.get_trader_by_name.return_value = trader
        self.zulu_ui.get_my_open_positions.return_value = df

        positions = self.trader._get_positions()
        assert len(positions) == 1



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

    def test_get_positions__(self):
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
