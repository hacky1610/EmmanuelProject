from pymongo.database import Database

class Market:

    def __init__(self, ticker:str, pip_euro:float):
        self.ticker = ticker
        self.pip_euro = pip_euro

    @staticmethod
    def Create(data:dict):
        m = Market(ticker=data["ticker"],
                      pip_euro=data["pip_euro"],
                      )
        return m

    def to_dict(self):
        return {"ticker": self.ticker, "pip_euro": self.pip_euro }



class MarketStore:

    def __init__(self, db: Database):

        self._collection = db["MarketStore"]

    def save(self, market: Market):
        existing_market = self._collection.find_one({"ticker": market.ticker})
        if existing_market:
            self._collection.update_one({"ticker":  market.ticker}, {"$set": market.to_dict()})
        else:
            self._collection.insert_one(market.to_dict())

    def get_market(self, ticker) -> Market:
        return Market.Create(self._collection.find_one({"ticker": ticker}))

