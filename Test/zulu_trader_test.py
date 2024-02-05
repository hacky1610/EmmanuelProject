import unittest
from datetime import datetime
from pandas import DataFrame, Series
from unittest.mock import MagicMock, patch

from BL.position import Position
from Connectors.market_store import Market
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
        self.tiingo = MagicMock()
        self.market_storage = MagicMock()
        self.trader = ZuluTrader(deal_storage=self.deal_storage,
                                 zulu_api=self.zulu_api,
                                 ig=self.ig,
                                 trader_store=self.trader_store,
                                 tracer=self.tracer,
                                 zulu_ui=self.zulu_ui,
                                 tiingo=self.tiingo,
                                 account_type="DEMO",
                                 market_storage=self.market_storage)

    def test_close_open_positions_pos_is_still_open(self):
        # Mock-Daten für get_open_deals und close
        open_deal = Deal(zulu_id="zID", dealReference="df", trader_id="tid", dealId="did",
                         direction="SELL", status="open", ticker="AAPL",
                         epic="AAPL.de", open_date_ig_str="", open_date_ig_datetime=None, stop_factor=1, limit_factor=1)
        df = DataFrame()
        df = df.append(Series(data=["zID"], index=["position_id"]), ignore_index=True)

        self.deal_storage.get_open_deals.return_value = [open_deal]
        self.zulu_ui.get_my_open_positions.return_value = df

        self.trader._close_open_positions()

        self.ig.close.assert_not_called()

    def test_close_open_positions_pos_is_closed(self):
        # Mock-Daten für get_open_deals und close
        open_deal = Deal(zulu_id="zID", dealReference="df", trader_id="tid", dealId="did",
                         direction="SELL", status="open", ticker="AAPL", epic="AAPL.de",
                         open_date_ig_str="", open_date_ig_datetime=None, close_date_ig_datetime=None,
                         stop_factor=1, limit_factor=1)
        df_open_pos = DataFrame()
        df_closed_pos = DataFrame()
        df_closed_pos = df_closed_pos.append(Series(data=["zID"], index=["position_id"]), ignore_index=True)

        self.deal_storage.get_open_deals.return_value = [open_deal]
        self.zulu_ui.get_my_open_positions.return_value = df_open_pos
        self.zulu_ui.get_my_closed_positions.return_value = df_closed_pos
        self.ig.close.return_value = (True, {"profit": 1.0})
        open_ig_deals = DataFrame()
        open_ig_deals = open_ig_deals.append(Series(data=["did"], index=["dealId"]), ignore_index=True)
        self.ig.get_opened_positions.return_value = open_ig_deals

        self.trader._close_open_positions()

        self.ig.close.assert_called()

    def test_close_open_positions_pos_cant_be_closed(self):
        # Mock-Daten für get_open_deals und close
        open_deal = Deal(zulu_id="zID", dealReference="df", trader_id="tid", dealId="did",
                         direction="SELL", status="open", ticker="AAPL", epic="AAPL.de",
                         open_date_ig_str="", open_date_ig_datetime=None, close_date_ig_datetime=None,
                         stop_factor=1, limit_factor=1)
        df_open_pos = DataFrame()
        df_closed_pos = DataFrame()
        df_closed_pos = df_closed_pos.append(Series(data=["zID"], index=["position_id"]), ignore_index=True)

        self.deal_storage.get_open_deals.return_value = [open_deal]
        self.zulu_ui.get_my_open_positions.return_value = df_open_pos
        self.zulu_ui.get_my_closed_positions.return_value = df_closed_pos
        self.ig.close.return_value = (False, {"profit": 1.0})
        open_ig_deals = DataFrame()
        open_ig_deals = open_ig_deals.append(Series(data=["did"], index=["dealId"]), ignore_index=True)
        self.ig.get_opened_positions.return_value = open_ig_deals


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
        self.trader_store.get_trader_by_name.return_value = Trader(id="id", name="name")
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
        positions = DataFrame()
        positions = positions.append(Series(data=["1", "bsahb", "BUY", "AAPL"],
                                            index=["position_id", "trader_id", "direction", "ticker"]),
                                     ignore_index=True)
        self.trader._get_positions = MagicMock(return_value=positions)
        markets = [{"symbol": "AAPL",
                    "epic": "AAPL_EPIC",
                    "currency": "USD"},
                   {"symbol": "GOO",
                    "epic": "GOO_EPIC",
                    "currency": "USD"},
                   ]
        self.ig.get_markets.return_value = markets
        trader = Trader(id="id", name="name")
        trader.hist = MagicMock()
        trader.hist.trader_performance.return_value = (True, "OK")
        self.trader_store.get_trader_by_id.return_value = trader
        self.trader._open_new_positions()

    def test_trade_position_position_is_aleady_open(self):
        # Mock-Daten für _deal_storage, _ig, _get_market_by_ticker und _zulu_api

        self.deal_storage.has_id.return_value = True
        markets = [{"symbol": "AAPL",
                    "epic": "AAPL_EPIC",
                    "currency": "USD"},
                   {"symbol": "GOO",
                    "epic": "GOO_EPIC",
                    "currency": "USD"},
                   ]
        trader = Trader(id="id", name="name")
        trader.hist = MagicMock()
        trader.hist.trader_performance.return_value = (True, "OK")
        self.trader_store.get_trader_by_id.return_value = trader
        self.trader._trade_position(markets, "123", "AAPL", "5431", "SELL")

        self.ig.open.assert_not_called()

    def test_trade_position_position_of_same_trader(self):
        # Mock-Daten für _deal_storage, _ig, _get_market_by_ticker und _zulu_api

        self.deal_storage.has_id.return_value = False
        self.deal_storage.position_of_same_trader.return_value = True
        markets = [{"symbol": "AAPL",
                    "epic": "AAPL_EPIC",
                    "currency": "USD"},
                   {"symbol": "GOO",
                    "epic": "GOO_EPIC",
                    "currency": "USD"},
                   ]
        trader = Trader(id="id", name="name")
        trader.hist = MagicMock()
        trader.hist.trader_performance.return_value = (True, "OK")
        self.trader_store.get_trader_by_id.return_value = trader
        self.trader._trade_position(markets, "123", "AAPL", "5431", "SELL")

        self.ig.open.assert_not_called()

    def test_trade_position(self):
        # Mock-Daten für _deal_storage, _ig, _get_market_by_ticker und _zulu_api

        self.deal_storage.has_id.return_value = False
        self.deal_storage.position_is_open.return_value = False
        self.market_storage.get_market.return_value = Market("Foo", 1)
        markets = [{"symbol": "AAPL",
                    "epic": "AAPL_EPIC",
                    "currency": "USD"},
                   {"symbol": "GOO",
                    "epic": "GOO_EPIC",
                    "currency": "USD"},
                   ]
        self.ig.open.return_value = (
            True, {"dealReference": "abgggggg", "dealId": "adhu", "date": "2021-01-01T20:20:00"})
        self.trader._get_market_by_ticker_or_none = MagicMock(
            return_value={"epic": "ghadh", "currency": "EUR", "scaling": 10, })
        self.trader._is_good_ig_trader = MagicMock(return_value=True)
        trader = Trader(id="id", name="name")
        trader.hist = MagicMock()
        trader.hist.trader_performance.return_value = (True, "OK")
        trader.hist.get_stop_distance.return_value = 1
        self.trader_store.get_trader_by_id.return_value = trader
        self.trader._trade_position(markets, "123", "AAPL", "5431", "SELL")

        self.ig.open.assert_called()

    def test_trade(self):
        self.trader._is_crash = MagicMock(return_value=False)

        self.trader.trade()

    def test_is_good_trader_no_check(self):
        self._check_trader_quality = False
        res = self.trader._is_good_ig_trader("124")
        assert res

    def test_is_good_trader_deals_less_than_3(self):
        self.trader._check_trader_quality = True
        deals = DataFrame()
        self.deal_storage.get_deals_of_trader_as_df = MagicMock(return_value=deals)
        res = self.trader._is_good_ig_trader("124")
        assert not res

    def test_is_good_trader_bad_results(self):
        self.trader._check_trader_quality = True
        deals = DataFrame()
        deals = deals.append(Series(data=[10],index=["profit"]), ignore_index=True)
        deals = deals.append(Series(data=[10],index=["profit"]), ignore_index=True)
        deals = deals.append(Series(data=[10],index=["profit"]), ignore_index=True)

        self.deal_storage.get_deals_of_trader_as_df = MagicMock(return_value=deals)
        res = self.trader._is_good_ig_trader("124")
        assert not res

    def test_is_good_trader_good_results(self):
        self.trader._check_trader_quality = True
        deals = DataFrame()
        deals = deals.append(Series(data=[80], index=["profit"]), ignore_index=True)
        deals = deals.append(Series(data=[10], index=["profit"]), ignore_index=True)
        deals = deals.append(Series(data=[10], index=["profit"]), ignore_index=True)

        self.deal_storage.get_deals_of_trader_as_df = MagicMock(return_value=deals)
        res = self.trader._is_good_ig_trader("124")
        assert  res



if __name__ == '__main__':
    unittest.main()
