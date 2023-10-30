import time

from BL import ConfigReader
from BL.zulu_trader import ZuluTrader
from Connectors.IG import IG
from Connectors.deal_store import DealStore
from Connectors.trader_store import TraderStore
from Connectors.zulu_api import ZuluApi
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.LogglyTracer import LogglyTracer

import pymongo

from Tracing.multi_tracer import MultiTracer

# Verbindung zur MongoDB-Datenbank herstellen
client = pymongo.MongoClient("mongodb://localhost:27017")
db = client["ZuluDB"]
ts = TraderStore(db)
ds = DealStore(db)


type_ = "DEMO"
if type_ == "DEMO":

    live = False
else:
    live = True

conf_reader = ConfigReader(live_config=live)
tracer = MultiTracer([LogglyTracer(conf_reader.get("loggly_api_key"), type_), ConsoleTracer()])
zuluApi = ZuluApi(tracer)
ig = IG(tracer=tracer, conf_reader=conf_reader, live=live)

p = ig.get_opened_positions()
zulu_trader = ZuluTrader(deal_storage=ds, zulu_api=zuluApi, ig=ig, trader_store=ts, tracer=tracer)

while True:
    zulu_trader.trade()
    time.sleep(60 * 5)


