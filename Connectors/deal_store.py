import datetime
from typing import List, Optional

from bson import ObjectId
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
                 manual_stop_level: float = None,
                 is_manual_stop: bool = False,
                 manual_stop:float = None,
                 touched_50:bool = False,
                 reached_level:bool = False,
                 closed_by_error:bool = False,
                 current_profit_percentage: float = 0.0,
                 next_dragen_deal_id: ObjectId = None,
                 predictor_object = None,
                 ):
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
        self.manual_stop_level = manual_stop_level
        self.touched_50 = touched_50
        self.reached_level = reached_level
        self.closed_by_error = closed_by_error
        self.current_profit_percentage = current_profit_percentage
        self.next_dragen_deal_id = next_dragen_deal_id
        self.predictor_object = predictor_object

    @staticmethod
    def Create(data: dict):
        return Deal(
            dealId=data["dealId"],
            direction=data["direction"],
            ticker=data["ticker"],
            dealReference=data["dealReference"],
            epic=data["epic"],
            size=data.get("size",1.0),
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
            is_manual_stop=data.get("is_manual_stop", False),
            manual_stop_level=data.get("manual_stop_level", None),
            touched_50=data.get("touched_50", False),
            reached_level=data.get("reached_level", False),
            closed_by_error=data.get("closed_by_error", False),
            current_profit_percentage=data.get("current_profit_percentage", 0.0),
            next_dragen_deal_id=data.get("next_dragen_deal_id",None),
            predictor_object=data.get("predictor_object", None)
        )

    def __str__(self):
        return f"{self.epic} {self.direction} {self.size} {self.open_date_ig_str} {self.close_date_ig_datetime} {self.profit} "

    def close(self):
        self.status = "Closed"

    def is_closed(self):
        return self.status == "Closed"

    def close_by_error(self):
        self.closed_by_error = True
        if self.current_profit_percentage > 0:
            self.profit = 5
        else:
            self.profit = -5
        self.status = "Closed"

    def get_next_dragen_id(self):
        return self.next_dragen_deal_id

    def set_next_dragen_id(self, dragen_id):
        self.next_dragen_deal_id = dragen_id

    def get_predictor_scan_id(self):
        return self.predictor_scan_id

    def get_open_time(self) -> datetime:
        return self.open_date_ig_datetime

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
            "size": self.size,
            "manual_stop_level":self.manual_stop_level,
            "touched_50": self.touched_50,
            "reached_level": self.reached_level,
            "closed_by_error": self.closed_by_error,
            "current_profit_percentage": self.current_profit_percentage,
            "next_dragen_deal_id": self.next_dragen_deal_id,
            "predictor_object": self.predictor_object

        }


class DealStore:

    def __init__(self, db: Database, account_type: str):

        self._collection = db["DealsTI"]
        self._account_type = account_type

    def save(self, deal: Deal):
        if self._collection.find_one({"open_date_ig_str": deal.open_date_ig_str, "account_type": self._account_type}):
            self._collection.update_one({"open_date_ig_str": deal.open_date_ig_str,
                                         "account_type": self._account_type}, {"$set": deal.to_dict()})
            return None
        else:
            deal.account_type = self._account_type  #TODO
            inserted_element = self._collection.insert_one(deal.to_dict())
            return inserted_element.inserted_id

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

    def get_all_deals_opened_after(self):
        date_filter = datetime.datetime(2025, 3, 23, hour=22)

        query = {
            "account_type": self._account_type,
            "open_date_ig_datetime": {"$gte": date_filter},
            "status": "Closed"
        }

        return self._collection.find(query)

    def get_open_deals(self) -> List[Deal]:
        deals = []
        for d in self._collection.find({"status": "open", "account_type": self._account_type}):
            deals.append(Deal.Create(d))
        return deals

    def get_open_deals_by_ticker(self, ticker: str) -> List[Deal]:
        deals = []
        for d in self._collection.find(
                {"status": "open", "ticker": ticker, "account_type": self._account_type}):
            deals.append(Deal.Create(d))
        return deals

    def get_closed_deals_by_ticker(self, ticker: str) -> List[Deal]:
        deals = []
        for d in self._collection.find(
                {"status": "Closed", "ticker": ticker, "account_type": self._account_type}):
            deals.append(Deal.Create(d))
        return deals

    def get_closed_deals_by_ticker_df(self, ticker: str) -> DataFrame:
        return DataFrame(list(self._collection.find(
            {"status": "Closed", "ticker": ticker})))

    def get_closed_deals_by_ticker_not_older_than_df(self, ticker: str, days:int) -> DataFrame:


        return DataFrame(list(self._collection.find(
            {"status": "Closed",
             "ticker": ticker,
             "close_date_ig_datetime": {"$gte": datetime.datetime.now() - datetime.timedelta(days=days)}
             } )))

    def get_closed_deals(self):
        return self._collection.find(
            {"status": "Closed"})

    def get_open_deals_raw(self):
        return self._collection.find(
            {"status": "open"})

    def get_custom(self, query:dict):
        return self._collection.find(query)

    def clear(self):
        self._collection.delete_many({"account_type": self._account_type})
