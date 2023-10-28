from pymongo.database import Database

from BL.trader_history import TraderHistory


class Trader:

    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.hist:TraderHistory

    def to_dict(self):
        return {"id":self.id, "name":self.name, "history": self.hist._hist}




class TraderStore:

    def __init__(self, db:Database):

        self._collection = db["TraderStore"]

    def add(self, trader: Trader):
        if not self._collection.find_one({"id": trader.id}):
            # Wenn die ID nicht existiert, fügen wir einen neuen Datensatz hinzu
            self._collection.insert_one(trader.to_dict())

    def save(self, trader:Trader):
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

    def get_all_traders(self):
        return  self._collection.find()
