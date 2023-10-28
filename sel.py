from BL import ConfigReader
from BL.zulu_trader import ZuluTrader
from Connectors.IG import IG
from Connectors.deal_store import DealStore
from Connectors.trader_store import TraderStore
from Connectors.zulu_api import ZuluApi
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.LogglyTracer import LogglyTracer

import pymongo

# Verbindung zur MongoDB-Datenbank herstellen
client = pymongo.MongoClient("mongodb://localhost:27017")
db = client["ZuluDB"]
ts = TraderStore(db)
ds = DealStore(db)
zuluApi = ZuluApi()


type_ = "DEMO"
if type_ == "DEMO":

    live = False
else:
    live = True

conf_reader = ConfigReader(live_config=live)
#tracer = LogglyTracer(conf_reader.get("loggly_api_key"), type_)
tracer = ConsoleTracer()
ig = IG(tracer=tracer, conf_reader=conf_reader, live=live)


zulu_trader = ZuluTrader(deal_storage=ds, zuluAPI=zuluApi, ig=ig, trader_store=ts, tracer=tracer)
zulu_trader.trade()


print("Finish")
