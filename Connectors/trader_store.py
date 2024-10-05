from typing import List
from pandas import DataFrame, Series
from pymongo.database import Database
from BL.trader_history import TraderHistory
from Connectors.market_store import MarketStore


class Trader:

    def __init__(self, trader_id: str, name: str, stop: int = 0, limit: int = 0):
        self.id = trader_id
        self.name = name
        self.stop = stop
        self.limit = limit
        self.hist: TraderHistory = TraderHistory({})

    @staticmethod
    def create(data: dict):
        trader = Trader(trader_id=data["id"],
                        name=data["name"],
                        stop=data.get("stop", 0),
                        limit=data.get("limit", 0)
                        )
        trader.hist = TraderHistory(data.get("history", {}))
        return trader

    def to_dict(self):
        return {"id": self.id,
                "name": self.name,
                "history": self.hist._hist,
                "stop": self.stop,
                "limit": self.limit}

    def calc_ig(self, market_store: MarketStore):
        self.stop, self.limit = self.hist.calc_ig_profit(market_store)

    def get_statistic(self):
        s = self.hist.get_series()
        s["name"] = self.name
        s["id"] = self.id

        return s


class TraderStore:

    def __init__(self, db: Database):

        self._collection = db["TraderStore"]

    def add(self, trader: Trader):
        if not self._collection.find_one({"id": trader.id}):
            self._collection.insert_one(trader.to_dict())
            print(f"Added new trader {trader.name}")

    def save(self, trader: Trader):
        existing_trader = self._collection.find_one({"id": trader.id})
        if existing_trader:
            self._collection.update_one({"id": trader.id}, {"$set": trader.to_dict()})
        else:
            self._collection.insert_one(trader.to_dict())

    def get_trader_by_id(self, trader_id) -> Trader:
        return Trader.create(self._collection.find_one({"id": trader_id}))

    def get_trader_by_name(self, name) -> Trader:
        return Trader.create(self._collection.find_one({"name": name}))

    def get_all_traders(self) -> List[Trader]:
        ids = list(self._collection.find({}, {'id': 1}))
        for trader_id in ids:
            yield self.get_trader_by_id(trader_id["id"])

    def get_all_trades_df(self) -> DataFrame:
        df = DataFrame()
        for trader in self.get_all_traders():
            s = Series(
                data=[trader.id, trader.name,
                      trader.hist.get_result(),
                      trader.hist.get_wl_ratio(),
                      trader.hist.get_wl_ratio_100(),
                      trader.hist.get_wl_ratio_20(),
                      trader.hist.get_avg_seconds()],
                index=["id", "name", "profit", "wl_ratio", "wl_ratio_100", "wl_ratio_20", "avg_open_time"])
            df = df.append(s, ignore_index=True)

        df = df.sort_values(by=["wl_ratio"], ascending=False)
        best = df[df.wl_ratio > 0.75]

        return best