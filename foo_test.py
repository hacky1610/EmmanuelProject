import os
import time

import pymongo

from BL.analytics import Analytics
from BL.indicators import Indicators
from Connectors.deal_store import DealStore
from Connectors.dropbox_cache import DropBoxCache
from Connectors.dropboxservice import DropBoxService
from Connectors.market_store import MarketStore
from Connectors.tiingo import TradeType, Tiingo
from Predictors.generic_predictor import GenericPredictor
from Tracing.LogglyTracer import LogglyTracer
from Connectors.IG import IG
from BL import EnvReader, DataProcessor, ConfigReader
from BL.trader import Trader
import dropbox



account_type = "DEMO"
conf_reader = ConfigReader(False)

dataProcessor = DataProcessor()
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx,"DEMO")
cache = DropBoxCache(ds)
tracer = LogglyTracer(conf_reader.get("loggly_api_key"), account_type)
tiingo = Tiingo(tracer=tracer, conf_reader=conf_reader, cache=cache)
ig = IG(conf_reader=conf_reader, tracer=tracer, live=False)
predictor_class_list = [GenericPredictor]
client = pymongo.MongoClient(f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ms = MarketStore(db)
ds = DealStore(db, account_type)
analytics = Analytics(ms, tracer)
indicators = Indicators(tracer=tracer)

markets = ig.get_markets(trade_type=TradeType.FX, tradeable=False)

for m in markets:
    print(f"Fix {m['symbol']}")
    p = GenericPredictor(cache=cache, indicators=indicators)
    p = p.load(m["symbol"])
    p.stop = 65
    p.limit = 20
    p.save(m["symbol"])



print("")
