from pandas import DataFrame, Series
from pymongo.database import Database

from BL.trader_history import TraderHistory


class Trader:

    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.hist: TraderHistory = TraderHistory({})

    def to_dict(self):
        return {"id": self.id, "name": self.name, "history": self.hist._hist}

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
            # Wenn die ID nicht existiert, fügen wir einen neuen Datensatz hinzu
            self._collection.insert_one(trader.to_dict())
            print(f"Added new trader {trader.name}")

    def save(self, trader: Trader):
        existing_trader = self._collection.find_one({"id": trader.id})
        if existing_trader:
            # Wenn die ID bereits existiert, aktualisieren wir den Datensatz
            self._collection.update_one({"id": trader.id}, {"$set": trader.to_dict()})
        else:
            # Wenn die ID nicht existiert, fügen wir einen neuen Datensatz hinzu
            self._collection.insert_one(trader.to_dict())

    def get_trader_by_id(self, trader_id):
        trader = self._collection.find_one({"id": trader_id})
        return trader

    def get_trader_by_name(self, name):
        return self._collection.find_one({"name": name})

    def get_all_traders(self):
        return self._collection.find()

    def get_all_trades_df(self) -> DataFrame:
        df = DataFrame()
        for trader in self.get_all_traders():
            hist = TraderHistory(trader["history"])
            s = Series(
                data=[trader["id"], trader["name"], hist.get_result(), hist.get_wl_ratio(), hist.get_wl_ratio_100(),
                      hist.get_wl_ratio_20(), hist.get_avg_seconds()],
                index=["id", "name", "profit", "wl_ratio", "wl_ratio_100", "wl_ratio_20", "avg_open_time"])
            df = df.append(s, ignore_index=True)

        df = df.sort_values(by=["wl_ratio"], ascending=False)
        best = df[df.wl_ratio > 0.75]

        return best
