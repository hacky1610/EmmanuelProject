import datetime
from typing import List, Optional

from pandas import DataFrame
from pymongo.database import Database
from pymongo.results import UpdateResult


class Deal:

    def __init__(self, ticker: str,
                 dealReference: str, dealId: str,
                 epic: str,
                 size: float,
                 open_date_ig_str: str,
                 open_date_ig_datetime: datetime,
                 direction: str,
                 stop_factor: int,
                 limit_factor: int,
                 close_date_ig_datetime: datetime = None,
                 status: str = "open",
                 profit: float = 0.0,
                 result: int = 0,
                 account_type: str = "DEMO",
                 intelligent_stop_used: bool = False,
                 intelligent_stop_level: float = None,
                 predictor_scan_id="",
                 open_level: float = None,
                 close_level: float = None,
                 is_manual_stop: bool = False,
                 manual_stop:float = None):
        self.ticker = ticker
        self.status = status
        self.dealId = dealId
        self.size = size
        self.direction = direction
        self.dealReference = dealReference
        self.epic = epic
        self.profit = profit
        self.account_type = account_type
        self.open_date_ig_str = open_date_ig_str
        self.open_date_ig_datetime = open_date_ig_datetime
        self.close_date_ig_datetime = close_date_ig_datetime
        self.result = result
        self.stop_factor = stop_factor
        self.limit_factor = limit_factor
        self.intelligent_stop_used = intelligent_stop_used
        self.intelligent_stop_level = intelligent_stop_level
        self.predictor_scan_id = predictor_scan_id
        self.open_level = open_level
        self.close_level = close_level
        self.manual_stop = manual_stop
        self.is_manual_stop = is_manual_stop

    @staticmethod
    def Create(data: dict):
        return Deal(
            dealId=data["dealId"],
            direction=data["direction"],
            ticker=data["ticker"],
            dealReference=data["dealReference"],
            epic=data["epic"],
            size=data["size"],
            status=data["status"],
            account_type=data.get("account_type", "DEMO"),
            profit=data.get("profit", 0.0),
            result=data.get("result", 0),
            open_date_ig_str=data["open_date_ig_str"],
            open_date_ig_datetime=data.get("open_date_ig_datetime", None),
            close_date_ig_datetime=data.get("close_date_ig_datetime", None),
            stop_factor=data.get("stop_factor", 20),
            limit_factor=data.get("limit_factor", 20),
            intelligent_stop_used=data.get("intelligent_stop_used", False),
            intelligent_stop_level=data.get("intelligent_stop_level", None),
            predictor_scan_id=data.get("predictor_scan_id", ""),
            open_level=data.get("open_level", None),
            close_level=data.get("close_level", None),
            manual_stop=data.get("manual_stop", None),
            is_manual_stop=data.get("is_manual_stop", False)
        )

    def __str__(self):
        return f"{self.epic} {self.direction}"

    def close(self):
        self.status = "Closed"

    def set_intelligent_stop_level(self, level: float):
        self.intelligent_stop_used = True
        self.intelligent_stop_level = level

    def to_dict(self):
        return {
            "ticker": self.ticker,
            "status": self.status,
            "dealReference": self.dealReference,
            "dealId": self.dealId,
            "epic": self.epic,
            "direction": self.direction,
            "profit": self.profit,
            "account_type": self.account_type,
            "open_date_ig_str": self.open_date_ig_str,
            "open_date_ig_datetime": self.open_date_ig_datetime,
            "close_date_ig_datetime": self.close_date_ig_datetime,
            "result": self.result,
            "stop_factor": self.stop_factor,
            "limit_factor": self.limit_factor,
            "intelligent_stop_used": self.intelligent_stop_used,
            "intelligent_stop_level": self.intelligent_stop_level,
            "predictor_scan_id": self.predictor_scan_id,
            "open_level": self.open_level,
            "close_level": self.close_level,
            "manual_stop":self.manual_stop,
            "is_manual_stop": self.is_manual_stop,
            "size": self.size
        }


class DealStore:

    def __init__(self, db: Database, account_type: str):

        self._collection = db["DealsTI"]
        self._account_type = account_type

    def save(self, deal: Deal):
        if self._collection.find_one({"open_date_ig_str": deal.open_date_ig_str, "account_type": self._account_type}):
            self._collection.update_one({"open_date_ig_str": deal.open_date_ig_str,
                                         "account_type": self._account_type}, {"$set": deal.to_dict()})
        else:
            deal.account_type = self._account_type  #TODO
            self._collection.insert_one(deal.to_dict())

    def get_deal_by_ig_id(self, ig_date: str, ticker: str) -> Optional[Deal]:
        res = self._collection.find_one(
            {"open_date_ig_str": ig_date, "ticker": ticker, "account_type": self._account_type})
        if res is not None:
            return Deal.Create(res)
        return None

    def get_deal_by_deal_id(self, deal_id: str) -> Optional[Deal]:
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
        for d in self._collection.find(
                {"status": "open", "ticker": ticker, "account_type": self._account_type}):
            deals.append(Deal.Create(d))
        return deals

    def get_closed_deals_by_ticker_df(self, ticker: str) -> DataFrame:
        return DataFrame(list(self._collection.find(
            {"status": "Closed", "ticker": ticker})))

    def get_closed_deals(self):
        return self._collection.find(
            {"status": "Closed"})

    def get_custom(self, query:dict):
        return self._collection.find(query)

    def clear(self):
        self._collection.delete_many({"account_type": self._account_type})
