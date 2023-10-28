from datetime import datetime

from pandas import DataFrame

from BL.position import Position
from Connectors.deal_store import Deal
from Connectors.tiingo import TradeType
from Connectors.zulu_api import ZuluApi
from Tracing.Tracer import Tracer


class ZuluTrader:


    def __init__(self, deal_storage, zuluAPI:ZuluApi, ig, trader_store, tracer:Tracer):
        self._deal_storage = deal_storage
        self._zuluApi = zuluAPI
        self._ig = ig
        self._max_minutes  = 6000
        self._trader_store = trader_store
        self._tracer = tracer

    def trade(self):
        self._close_open_positions()
        self._open_new_positions()

    def _is_still_open(self, trader_id:str, id:str):
        for op in self._zuluApi.get_opened_positions(trader_id, ""):
            if id == op.get_id():
                self._tracer.write(f"Position {op} is still open")
                return True
        self._tracer.write(f"Position {op}  is closed")
        return False
    def _close_open_positions(self):
        self._tracer.write("Close positions")
        for open_deal in self._deal_storage.get_open_deals():
            if not self._is_still_open(open_deal["trader_id"],open_deal["id"]):
                result, deal_respons = self._ig.close(epic=open_deal["epic"],
                                                direction=self._ig.get_inverse(open_deal["direction"]),
                                                deal_id=open_deal["deal_id"])
                if result:
                    self._tracer.write("Position closed")
                    self._deal_storage.update_state(open_deal["id"], "Closed")

    def _get_market_by_ticker(self, markets:DataFrame, ticker:str):
        for m in markets:
            if m["symbol"] == ticker:
                return m
        raise Exception("")

    def _open_new_positions(self):
        self._tracer.write("Open positions")

        markets = self._ig.get_markets(trade_type=TradeType.FX, tradeable=False)

        for p in self._get_positions():
            self._trade_position(markets, p)

    def _trade_position(self, markets:DataFrame, p:Position):
        if self._deal_storage.has_id(p.get_id()):
            self._tracer.write(f"Position {p} is already open")

        diff = datetime.utcnow() - p.get_open_time()
        if diff.seconds / 60 > self._max_minutes:
            self._tracer.warning(f"Position {p} is to old. Older than {self._max_minutes} minites")
            return

        m = self._get_market_by_ticker(markets, p.get_ticker())
        self._tracer.write(f"Try to open position {p}")
        result, deal_respons = self._ig.open(epic=m["epic"], direction=p.get_direction(),
                                             currency=m["currency"])
        if result:
            d = Deal(zulu_id=p.get_id(), ticker=p.get_ticker(),
                     dealReference=deal_respons["dealReference"],
                     dealId=deal_respons["dealId"], trader_id=p.get_trader_id(),
                     epic=m["epic"], direction=p.get_direction())
            self._deal_storage.save(d)
        else:
            self._tracer.error(f"Error while open position {p}")

    def _get_positions(self):
        positions = []
        for trader in self._trader_store.get_all_traders():
            positions = positions + self._zuluApi.get_opened_positions(trader["id"], trader["name"])
        return positions

