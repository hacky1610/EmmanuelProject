from datetime import datetime
from typing import List, Optional

from pandas import DataFrame

from BL.position import Position
from Connectors.IG import IG
from Connectors.deal_store import Deal, DealStore
from Connectors.tiingo import TradeType
from Connectors.zulu_api import ZuluApi
from Tracing.Tracer import Tracer


class ZuluTrader:

    def __init__(self, deal_storage: DealStore, zulu_api: ZuluApi, ig:IG, trader_store, tracer: Tracer):
        self._deal_storage = deal_storage
        self._zulu_api = zulu_api
        self._ig = ig
        self._max_minutes = 10
        self._trader_store = trader_store
        self._tracer = tracer

    def trade(self):
        self._close_open_positions()
        self._open_new_positions()

    def _is_still_open(self, trader_id: str, position_id: str):
        for op in self._zulu_api.get_opened_positions(trader_id, ""):
            if position_id == op.get_id():
                self._tracer.write(f"Position {op} is still open")
                return True
        self._tracer.write(f"Position with id {position_id} is closed")
        return False

    def _close_open_positions(self):
        self._tracer.write("Close positions")
        for open_deal in self._deal_storage.get_open_deals():
            if not self._is_still_open(open_deal["trader_id"], open_deal["id"]):
                result, _ = self._ig.close(direction=self._ig.get_inverse(open_deal["direction"]),
                                           deal_id=open_deal["dealId"])
                if result:
                    self._tracer.write(f"Position {open_deal['id']} closed")
                    self._deal_storage.update_state(open_deal["id"], "Closed")
                else:
                    self._tracer.error(f"Position {open_deal['id']} could not be closed")

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

        for p in self._get_positions():
            self._trade_position(markets, p)

    def _is_new_position(self,position: Position):
        diff = datetime.utcnow() - position.get_open_time()
        if diff.seconds / 60 > self._max_minutes:
            self._tracer.debug(f"Position {position} is to old. Older than {self._max_minutes} minites")
            return False
        self._tracer.write(f"Position {position} is new")
        return True

    def _trade_position(self, markets: DataFrame, position: Position):
        if self._deal_storage.has_id(position.get_id()):
            self._tracer.write(f"Position {position} is already open")
            return

        if self._deal_storage.position_of_same_trader(position.get_ticker(), position.get_trader_id()):
            self._tracer.write(f"There is already an open position of {position.get_ticker()} from trader {position.get_trader_id()}")
            return

        if not self._is_new_position(position):
            return

        m = self._get_market_by_ticker_or_none(markets, position.get_ticker())
        if m is None:
            self._tracer.warning(f"Could not find market for {position.get_ticker()}")
            return

        self._tracer.write(f"Try to open position {position}")
        result, deal_respons = self._ig.open(epic=m["epic"], direction=position.get_direction(),
                                             currency=m["currency"], limit=None, stop=None)
        if result:
            d = Deal(zulu_id=position.get_id(), ticker=position.get_ticker(),
                     dealReference=deal_respons["dealReference"],
                     dealId=deal_respons["dealId"], trader_id=position.get_trader_id(),
                     epic=m["epic"], direction=position.get_direction())
            self._deal_storage.save(d)
        else:
            self._tracer.error(f"Error while open position {position}")

    def _get_positions(self) -> List[Position]:
        positions = []
        best_traders = self._trader_store.get_all_trades_df()

        self._tracer.write(best_traders.filter(["name", "wl_ratio"]))
        for trader in best_traders.iterrows():
            positions = positions + self._zulu_api.get_opened_positions(trader[1]["id"], trader[1]["name"])
        return positions
