from pymongo.database import Database

class Market:

    def __init__(self, ticker:str, pip_euro:float):
        self.ticker = ticker
        self.pip_euro = pip_euro

    def get_euro_value(self, pips: float, scaling_factor: int = 1):
        return pips * scaling_factor / self.pip_euro

    def get_pip_value(self, euro: float, scaling_factor: int = 1):
        return self.pip_euro * euro / scaling_factor

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
        self._cache = {}

    def save(self, market: Market):
        existing_market = self._collection.find_one({"ticker": market.ticker})
        if existing_market:
            self._collection.update_one({"ticker":  market.ticker}, {"$set": market.to_dict()})
        else:
            self._collection.insert_one(market.to_dict())

    def get_market(self, ticker) -> Market:
        if ticker in self._cache:
            return self._cache[ticker]
        else:
            market_data = self._collection.find_one({"ticker": ticker})
            if market_data:
                market = Market.Create(market_data)
                # Add to cache for future use
                self._cache[ticker] = market
                return market
            else:
                #print(f"ERROR: no market for {ticker}")
                return None

