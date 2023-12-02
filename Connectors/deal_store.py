import datetime
from typing import List, Optional

from pandas import DataFrame
from pymongo.database import Database
from pymongo.results import UpdateResult

from BL.trader_history import TraderHistory


class Deal:

    def __init__(self, zulu_id: str, ticker: str,
                 dealReference: str, dealId: str,
                 trader_id: str, epic: str,
                 open_date_ig_str: str,
                 open_date_ig_datetime: datetime,
                 direction: str,
                 stop_factor: int,
                 limit_factor: int,
                 close_reason: str = "Unknown",
                 close_date_ig_datetime: datetime = None,
                 status: str = "open",
                 profit: float = 0.0,
                 result: int = 0,
                 account_type: str = "DEMO"):
        self.ticker = ticker
        self.id = zulu_id
        self.status = status
        self.dealId = dealId
        self.direction = direction
        self.dealReference = dealReference
        self.trader_id = trader_id
        self.epic = epic
        self.profit = profit
        self.account_type = account_type
        self.open_date_ig_str = open_date_ig_str
        self.open_date_ig_datetime = open_date_ig_datetime
        self.close_date_ig_datetime = close_date_ig_datetime
        self.result = result
        self.close_reason = close_reason
        self.stop_factor = stop_factor
        self.limit_factor = limit_factor

    @staticmethod
    def Create(data: dict):
        return Deal(zulu_id=data["id"],
                    dealId=data["dealId"],
                    trader_id=data["trader_id"],
                    direction=data["direction"],
                    ticker=data["ticker"],
                    dealReference=data["dealReference"],
                    epic=data["epic"],
                    status=data["status"],
                    account_type=data.get("account_type", "DEMO"),
                    profit=data.get("profit", 0.0),
                    result=data.get("result", 0),
                    close_reason=data.get("close_reason", "Unknown"),
                    open_date_ig_str=data["open_date_ig_str"],
                    open_date_ig_datetime=data.get("open_date_ig_datetime", None),
                    close_date_ig_datetime=data.get("close_date_ig_datetime", None),
                    stop_factor=data.get("stop_factor", 20),
                    limit_factor=data.get("limit_factor", 20))

    def __str__(self):
        return f"{self.id} - {self.epic} {self.direction} Trader ID: {self.trader_id}"

    def close(self, close_reason: str = "Unknown"):
        self.status = "Closed"
        self.close_reason = close_reason

    def to_dict(self):
        return {"id": self.id,
                "ticker": self.ticker,
                "status": self.status,
                "dealReference": self.dealReference,
                "dealId": self.dealId,
                "trader_id": self.trader_id,
                "epic": self.epic,
                "direction": self.direction,
                "profit": self.profit,
                "account_type": self.account_type,
                "open_date_ig_str": self.open_date_ig_str,
                "open_date_ig_datetime": self.open_date_ig_datetime,
                "close_date_ig_datetime": self.close_date_ig_datetime,
                "result": self.result,
                "close_reason": self.close_reason,
                "stop_factor": self.stop_factor,
                "limit_factor": self.limit_factor}


class DealStore:

    def __init__(self, db: Database, account_type: str):

        self._collection = db["Deals"]
        self._account_type = account_type

    def save(self, deal: Deal):
        if self._collection.find_one({"id": deal.id, "account_type": self._account_type}):
            self._collection.update_one({"id": deal.id,
                                         "account_type": self._account_type}, {"$set": deal.to_dict()})
        else:
            self._collection.insert_one(deal.to_dict())

    def get_deal_by_zulu_id(self, id):
        return self._collection.find_one({"id": id, "account_type": self._account_type})

    def get_deal_by_ig_id(self, ig_date: str, ticker: str) -> Optional[Deal]:
        res = self._collection.find_one(
            {"open_date_ig_str": ig_date, "ticker": ticker, "account_type": self._account_type})
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

    def has_id(self, id: str):
        return self._collection.find_one({"id": id, "account_type": self._account_type})

    def clear(self):
        self._collection.delete_many({ "account_type": self._account_type})

    def position_of_same_trader(self, ticker: str, trader_id):
        return self._collection.find_one(
            {"ticker": ticker, "trader_id": trader_id, "status": "open", "account_type": self._account_type})

    def position_is_open(self, ticker: str):
        return self._collection.find_one({"ticker": ticker, "status": "open", "account_type": self._account_type})

    def get_deals_of_trader_as_df(self, trader_id: str, consider_account_type: bool = True) -> DataFrame:
        query = {"trader_id": trader_id}
        if consider_account_type:
            query.update({"account_type": self._account_type})
        deals = self._collection.find(query)
        df = DataFrame(list(deals))

        return df
