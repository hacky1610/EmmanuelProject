import time
import traceback
from datetime import datetime
from pandas import DataFrame
from BL import ConfigReader
from BL.trader_history import TraderHistory
from Connectors.market_store import MarketStore
from Connectors.trader_store import TraderStore, Trader
from Connectors.zulu_api import ZuluApi
from Tracing.ConsoleTracer import ConsoleTracer
import pymongo
import random


def update_trader(trader:Trader, only_new = False):
    try:
        diff_days = trader.hist.get_diff_to_today()
        if only_new and diff_days != 1000:
            print("Trader known")
            return
        if diff_days < 100:
            hist = zuluApi.get_history(trader.id, pages=1, size=diff_days+ 10)
        else:
            hist = zuluApi.get_history(trader.id, pages=3, size=100)

        new_df = trader.hist._hist_df.append(hist._hist_df)
        new_df = new_df.drop_duplicates(subset=['tradeId'])
        trader.hist = TraderHistory(new_df.to_dict("records"))
        print(f"{trader.name} -> {trader.hist}")
        ts.save(trader)
        time.sleep(random.randint(120, 200))
    except Exception as ex:
        time.sleep(random.randint(120, 200))
        traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
        print(f"Error with {trader.name} {traceback_str}")

conf_reader = ConfigReader("DEMO")
client = pymongo.MongoClient(f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
zuluApi = ZuluApi(ConsoleTracer())
ts = TraderStore(db)
ms = MarketStore(db)
df = DataFrame()

for trader in ts.get_all_traders():
    try:
        update_trader(trader, False)
        df = df.append(trader.get_statistic(), ignore_index=True)
    except Exception as ex:
        time.sleep(random.randint(120, 200))
        traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
        print(f"Error with {trader.name} {traceback_str}")


df = df.sort_values(by=["ig_custom"], ascending=False)
df.to_html("/home/daniel/trader_stats.html")

