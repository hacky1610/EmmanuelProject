import time
from Connectors.trader_store import TraderStore, Trader
from Connectors.zulu_api import ZuluApi
from Tracing.ConsoleTracer import ConsoleTracer
import pymongo
import random

# Verbindung zur MongoDB-Datenbank herstellen
client = pymongo.MongoClient("mongodb://localhost:27017")
db = client["ZuluDB"]


zuluApi = ZuluApi(ConsoleTracer())

ts = TraderStore(db)
trader_list = []
for f in ts.get_all_traders():
    trader_list.append(f)

random.shuffle(trader_list)

for f in trader_list:
    trader = Trader(f["id"],f["name"])
    trader.hist = zuluApi.get_history(trader.id)
    print(f"{trader.name} -> {trader.hist}" )
    ts.save(trader)
    time.sleep(random.randint(44,120))


print("Updates history")

