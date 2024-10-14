import random
from datetime import datetime
from typing import List, Dict
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
        self.evaluation = []

    @staticmethod
    def create(data: dict):
        trader = Trader(trader_id=data["id"],
                        name=data["name"],
                        stop=data.get("stop", 0),
                        limit=data.get("limit", 0)
                        )
        trader.hist = TraderHistory(data.get("history", {}))
        trader.evaluation = data.get("evaluation", {})
        return trader

    def to_dict(self):
        return {"id": self.id,
                "name": self.name,
                "history": self.hist._hist,
                "stop": self.stop,
                "limit": self.limit,
                "evaluation": self.evaluation
                }

    def calc_ig(self, market_store: MarketStore):
        self.stop, self.limit = self.hist.calc_ig_profit(market_store)

    def get_statistic(self):
        s = self.hist.get_series()
        s["name"] = self.name
        s["id"] = self.id

        return s

    def set_evaluation(self,evaluation:List[Dict]):
        self.evaluation = evaluation

    def is_good(self, symbol:str):
        if len(self.evaluation) == 0:
            return False



        df = DataFrame(self.evaluation)
        df_symbol = df[df.symbol == symbol]

        if len(df_symbol) == 0:
            return False

        if "newest_trade" not in df_symbol.columns:
            return False

        try:
            time = df_symbol["newest_trade"].item()
            delta = datetime.now() - time
            if delta.days > 7:
                return False
        except Exception:
            return False

        if df_symbol.trades.sum() < 30:
            return False

        avg_profit = df_symbol.profit.sum() / df_symbol.trades.sum()
        if avg_profit < 5:
            return False



        return True

    def get_limit(self, symbol):

        if len(self.evaluation) == 0:
            return 0

        df = DataFrame(self.evaluation)
        df_symbol = df[df.symbol == symbol]

        if len(df_symbol) == 0:
            return 0

        return df_symbol.limit.mean()

    def get_stop(self, symbol):

        if len(self.evaluation) == 0:
            return 0

        df = DataFrame(self.evaluation)
        df_symbol = df[df.symbol == symbol]

        if len(df_symbol) == 0:
            return 0

        return df_symbol.stop.mean()

    def get_eval(self):
        return self.evaluation




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

    def get_trader_by_id(self, trader_id, load_history = False) -> Trader:
        if load_history:
            return Trader.create(self._collection.find_one({"id": trader_id}))
        else:
            return Trader.create(self._collection.find_one({"id": trader_id}, {"history":0}))

    def get_trader_by_name(self, name) -> Trader:
        return Trader.create(self._collection.find_one({"name": name}))

    def get_all_traders(self, load_history = False, shuffled:bool = False) -> List[Trader]:
        ids = list(self._collection.find({}, {'id': 1}))
        if shuffled:
            random.shuffle(ids)
        for trader_id in ids:
            yield self.get_trader_by_id(trader_id["id"], load_history)

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