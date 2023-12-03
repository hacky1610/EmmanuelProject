import time
import traceback

from pandas import DataFrame

from BL import ConfigReader
from Connectors.market_store import MarketStore
from Connectors.trader_store import TraderStore, Trader
from Connectors.zulu_api import ZuluApi
from Tracing.ConsoleTracer import ConsoleTracer
import pymongo
import random

conf_reader = ConfigReader("DEMO")
# Verbindung zur MongoDB-Datenbank herstellen
client = pymongo.MongoClient(f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")

db = client["ZuluDB"]


zuluApi = ZuluApi(ConsoleTracer())

ts = TraderStore(db)
ms = MarketStore(db)
trader_list = ts.get_all_traders()
random.shuffle(trader_list)

for trader in trader_list:
    try:
        trader.hist = zuluApi.get_history(trader.id,3)
        trader.calc_ig(ms)
        print(f"{trader.name} -> {trader.hist}" )
        ts.save(trader)
        time.sleep(random.randint(44,120))
    except Exception as ex:
        time.sleep(random.randint(44,120))
        traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
        print(f"Error with {trader.name} {traceback_str}")


df = DataFrame()

for trader in ts.get_all_traders():
    df = df.append(trader.get_statistic(), ignore_index=True)


df = df.sort_values(by=["wl_ratio"], ascending=False)
df.to_html("/home/daniel/trader_stats.html")

