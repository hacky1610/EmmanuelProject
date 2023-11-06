from datetime import datetime, timedelta
from typing import List, Optional
import time

from pandas import DataFrame, Series

from BL.position import Position
from BL.trader_history import TraderHistory
from Connectors.IG import IG
from Connectors.deal_store import Deal, DealStore
from Connectors.tiingo import TradeType
from Connectors.trader_store import TraderStore, Trader
from Connectors.zulu_api import ZuluApi
from Tracing.Tracer import Tracer
from UI.zulutrade import ZuluTradeUI


class ZuluTrader:

    def __init__(self, deal_storage: DealStore, zulu_api: ZuluApi, zulu_ui: ZuluTradeUI,
                 ig: IG, trader_store: TraderStore, tracer: Tracer):
        self._deal_storage = deal_storage
        self._zulu_api = zulu_api
        self._ig = ig
        self._max_minutes = 10
        self._trader_store = trader_store
        self._tracer = tracer
        self._zulu_ui = zulu_ui
        self._min_wl_ration = 0.67

    def trade(self):
        self._close_open_positions()
        self._open_new_positions()

    def update_trader_history(self):
        self._tracer.write("Update History")
        for trader in self._trader_store.get_all_traders():
            time.sleep(10)
            trader.hist = self._zulu_api.get_history(trader.id)
            print(f"{trader.name} -> {trader.hist}")
            self._trader_store.save(trader)


    def _is_still_open(self, trader_id: str, position_id: str):
        for op in self._zulu_api.get_opened_positions(trader_id, ""):
            if position_id == op.get_id():
                self._tracer.write(f"Position {op} is still open")
                return True
        self._tracer.write(f"Position with id {position_id} is closed")
        return False

    def _close_open_positions(self):
        self._tracer.write("Close positions")
        open_positons = self._zulu_ui.get_my_open_positions()
        for open_deal in self._deal_storage.get_open_deals():
            if len(open_positons[open_positons.position_id == open_deal["id"]]) == 0:
                self._tracer.write(f"Position {open_deal['id']} is closed")
                result, _ = self._ig.close(direction=self._ig.get_inverse(open_deal["direction"]),
                                           deal_id=open_deal["dealId"])
                if result:
                    self._tracer.write(f"Position {open_deal['id']} closed")
                    self._deal_storage.update_state(open_deal["id"], "Closed")
                else:
                    self._tracer.error(f"Position {open_deal['id']} could not be closed")
            else:
                self._tracer.write(f"Position {open_deal['id']} is still open")

    def _get_market_by_ticker_or_none(self, markets: DataFrame, ticker: str) -> Optional[dict]:
        for m in markets:
            if m["symbol"] == ticker:
                return m
        return None

    def _open_new_positions(self):
        self._tracer.write("Open positions")

        markets = self._ig.get_markets(trade_type=TradeType.FX, tradeable=True)
        if len(markets) == 0:
            self._tracer.write("market closed")
            return

        for p in self._get_positions().iterrows():
            self._trade_position(markets=markets,position_id=p[1].position_id,
                                 trader_id=p[1].trader_id, direction=p[1].direction, ticker=p[1].ticker)


    def _trade_position(self, markets: DataFrame, position_id:str, ticker:str, trader_id:str, direction:str):
        if self._deal_storage.has_id(position_id):
            self._tracer.write(f"Position {position_id} - {ticker} by {trader_id} is already open")
            return

        if self._deal_storage.position_of_same_trader(ticker, trader_id):
            self._tracer.write(
                f"There is already an open position of {ticker} from trader {trader_id}")
            return


        m = self._get_market_by_ticker_or_none(markets, ticker)
        if m is None:
            self._tracer.warning(f"Could not find market for {ticker}")
            return

        self._tracer.write(f"Try to open position {position_id} - {ticker} by {trader_id}")
        result, deal_respons = self._ig.open(epic=m["epic"], direction=direction,
                                             currency=m["currency"], limit=None, stop=None)
        if result:
            d = Deal(zulu_id=position_id, ticker=ticker,
                     dealReference=deal_respons["dealReference"],
                     dealId=deal_respons["dealId"], trader_id=trader_id,
                     epic=m["epic"], direction=direction)
            self._deal_storage.save(d)
        else:
            self._tracer.error(f"Error while open position {position_id} - {ticker} by {trader_id}")

    def _calc_hist(self,row):
        trader = self._trader_store.get_trader_by_name(row.trader_name)
        return trader.hist.get_wl_ratio()



    def _get_trader_id(self, row):
        trader = self._trader_store.get_trader_by_name(row.trader_name)
        return trader.id


    def _get_positions(self) -> DataFrame:
        positions = self._zulu_ui.get_my_open_positions()
        if len(positions) == 0:
            self._tracer.write("No open positions")
            return positions

        #Filter for time
        positions = positions[positions.time >= datetime.now() - timedelta(minutes=45)]
        if len(positions) == 0:
            self._tracer.write("All postions are to old")
            return positions

        positions["wl_ratio"] = positions.apply(self._calc_hist, axis=1)
        positions["trader_id"] = positions.apply(self._get_trader_id, axis=1)

        #Filter for quality
        good_positions = positions[positions.wl_ratio > self._min_wl_ration]
        if len(good_positions) == 0:
            self._tracer.write(f"All postions are from bad traders. This postions are bad: \n {positions[positions.wl_ratio <= self._min_wl_ration]}")
            return good_positions

        good_positions = good_positions.sort_values(by=["wl_ratio"], ascending=False)

        self._tracer.write(f"new positions: {good_positions.filter(['time','ticker', 'wl_ratio', 'trader_id', 'trader_name', 'direction'])}")
        return good_positions
