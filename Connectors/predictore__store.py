import datetime
from typing import List, Optional

from pandas import DataFrame
from pymongo.database import Database
from pymongo.results import UpdateResult




class DealStore:

    def __init__(self, db: Database, account_type: str):

        self._collection = db["DealsTI"]
        self._account_type = account_type

    def save(self, deal: Deal):
        if self._collection.find_one({"open_date_ig_str": deal.open_date_ig_str, "account_type": self._account_type}):
            self._collection.update_one({"open_date_ig_str": deal.open_date_ig_str,
                                         "account_type": self._account_type}, {"$set": deal.to_dict()})
        else:
            self._collection.insert_one(deal.to_dict())

    def get_deal_by_ig_id(self, ig_date: str, ticker: str) -> Optional[Deal]:
        res = self._collection.find_one(
            {"open_date_ig_str": ig_date, "ticker": ticker, "account_type": self._account_type})
        if res is not None:
            return Deal.Create(res)
        return None

    def get_deal_by_deal_id(self, deal_id:str):
        res = self._collection.find_one(
            {"dealId": deal_id, "account_type": self._account_type})
        if res is not None:
            return Deal.Create(res)
        return None



    def get_all_deals(self):
        return self._collection.find({"account_type": self._account_type})

    def get_open_deals(self) -> List[Deal]:
        deals = []
        for d in self._collection.find({"status": "open", "account_type": self._account_type}):
            deals.append(Deal.Create(d))
        return deals

    def get_open_deals_by_ticker(self, ticker: str) -> List:
        deals = []
        for d in  self._collection.find(
            {"status": "open", "ticker": ticker, "account_type": self._account_type}):
            deals.append(Deal.Create(d))
        return deals


    def clear(self):
        self._collection.delete_many({ "account_type": self._account_type})

