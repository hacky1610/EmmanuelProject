from typing import List

from pymongo.database import Database

from BL.trader_history import TraderHistory


class Deal:

    def __init__(self, zulu_id: str, ticker: str,
                 dealReference: str, dealId: str,
                 trader_id: str, epic: str,
                 direction: str,
                 status: str = "open"):
        self.ticker = ticker
        self.id = zulu_id
        self.status = status
        self.dealId = dealId
        self.direction = direction
        self.dealReference = dealReference
        self.trader_id = trader_id
        self.epic = epic

    @staticmethod
    def Create(data: dict):
        return Deal(zulu_id=data["id"],
                    dealId=data["dealId"],
                    trader_id=data["trader_id"],
                    direction=data["direction"],
                    ticker=data["ticker"],
                    dealReference=data["dealReference"],
                    epic=data["epic"],
                    status=data["status"])

    def __str__(self):
        return f"{self.id} - {self.epic} {self.direction} Trader ID: {self.trader_id}"

    def to_dict(self):
        return {"id": self.id,
                "ticker": self.ticker,
                "status": self.status,
                "dealReference": self.dealReference,
                "dealId": self.dealId,
                "trader_id": self.trader_id,
                "epic": self.epic,
                "direction": self.direction}


class DealStore:

    def __init__(self, db: Database):

        self._collection = db["Deals"]

    def save(self, deal: Deal):
        if self._collection.find_one({"id": deal.id}):
            self._collection.update_one({"id": deal.id}, {"$set": deal.to_dict()})
        else:
            self._collection.insert_one(deal.to_dict())

    def update_state(self, id: str, state: str):
        if self.has_id(id):
            self._collection.update_one({"id": id}, {"$set": {"status": state}})
            print("Attribut state wurde erfolgreich geändert.")
        else:
            print("Element mit ID {} wurde nicht gefunden.".format(id))

    def get_deal_by_id(self, id):
        return self._collection.find_one({"id": id})

    def get_all_deals(self):
        return self._collection.find()

    def get_open_deals(self) -> List[Deal]:
        deals = []
        for d in self._collection.find({"status": "open"}):
            deals.append(Deal.Create(d))
        return deals

    def has_id(self, id: str):
        return self._collection.find_one({"id": id})

    def clear(self):
        self._collection.delete_many({})

    def position_of_same_trader(self, ticker: str, trader_id):
        return self._collection.find_one({"ticker": ticker, "trader_id": trader_id})
