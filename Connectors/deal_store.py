from pymongo.database import Database

from BL.trader_history import TraderHistory




class Deal:

    def __init__(self, zulu_id:str, ticker:str,
                 dealReference:str, dealId:str,
                 trader_id:str, epic:str,
                 direction:str,
                 status:str = "open"):
        self.ticker = ticker
        self.id = zulu_id
        self.status = status
        self.dealId = dealId
        self.direction = direction
        self.dealReference = dealReference
        self.trader_id = trader_id
        self.epic = epic


    def to_dict(self):
        return {"id": self.id,
                "ticker": self.ticker,
                "status": self.status,
                "dealReference":self.dealReference,
                "dealId": self.dealId,
                "trader_id": self.trader_id,
                "epic": self.epic,
                "direction": self.direction}

class DealStore:

    def __init__(self, db:Database):

        self._collection = db["Deals"]

    def save(self, deal:Deal):
        existing_trader = self._collection.find_one({"id": deal.id})
        if existing_trader:
            # Wenn die ID bereits existiert, aktualisieren wir den Datensatz
            self._collection.update_one({"id": deal.id}, {"$set": deal.to_dict()})
        else:
            # Wenn die ID nicht existiert, fügen wir einen neuen Datensatz hinzu
            self._collection.insert_one(deal.to_dict())

    def update_state(self, id:str, state:str):
        if self.has_id(id):
            self._collection.update_one({"id": id}, {"$set": {"status": state}})
            print("Attribut 'Foo' wurde erfolgreich geändert.")
        else:
            print("Element mit ID {} wurde nicht gefunden.".format(id))

    def get_deal_by_id(self, id):
        return self._collection.find_one({"id": id})

    def get_all_deals(self):
        return  self._collection.find()

    def get_open_deals(self):
        return self._collection.find({"status": "open"})

    def has_id(self, id:str):
        return self._collection.find_one({"id": id})

