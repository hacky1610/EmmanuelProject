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


def update_trader(trader:Trader):
    try:
        last_d = TraderHistory._unix_timestamp_to_datetime(trader.hist._hist_df[-1:].dateClosed)
        diff = datetime.now() - last_d
        if diff.days < 100:
            hist = zuluApi.get_history(trader.id, pages=1, size=diff.days + 10)
        else:
            hist = zuluApi.get_history(trader.id, pages=3, size=100)

        new_df = trader.hist._hist_df.append(hist._hist_df)
        new_df = new_df.drop_duplicates(subset=['Val'])
        trader.hist = TraderHistory(new_df.to_dict())
        trader.calc_ig(ms)
        print(f"{trader.name} -> {trader.hist}")
        ts.save(trader)
        time.sleep(random.randint(120, 200))
    except Exception as ex:
        time.sleep(random.randint(120, 200))
        traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
        print(f"Error with {trader.name} {traceback_str}")

conf_reader = ConfigReader("DEMO")
# Verbindung zur MongoDB-Datenbank herstellen
client = pymongo.MongoClient(f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")

db = client["ZuluDB"]

zuluApi = ZuluApi(ConsoleTracer())

ts = TraderStore(db)
ms = MarketStore(db)

t = ts.get_trader_by_name("AMOSTIL123")

update_trader(t)

trader_list = ts.get_all_traders()
random.shuffle(trader_list)





for trader in trader_list:
    update_trader(trader)

df = DataFrame()

for trader in ts.get_all_traders():
    try:
        df = df.append(trader.get_statistic(), ignore_index=True)
    except Exception as ex:
        time.sleep(random.randint(120, 200))
        traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
        print(f"Error with {trader.name} {traceback_str}")


df = df.sort_values(by=["ig_custom"], ascending=False)
df.to_html("/home/daniel/trader_stats.html")

