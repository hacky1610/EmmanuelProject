import time

from pandas import DataFrame
from selenium import webdriver

from BL.trader_history import TraderHistory
from Connectors.trader_store import TraderStore, Trader
from Connectors.zulu_api import ZuluApi
from Tracing.ConsoleTracer import ConsoleTracer
from UI.zulutrade import ZuluTradeUI
import pymongo

# Verbindung zur MongoDB-Datenbank herstellen
client = pymongo.MongoClient("mongodb://localhost:27017")
db = client["ZuluDB"]


ts = TraderStore(db)
df = DataFrame()

for f in ts.get_all_traders():
    trader = Trader(f["id"],f["name"])
    trader.hist = TraderHistory(f["history"])
    #trader.hist.show()
    df = df.append(trader.get_statistic(), ignore_index=True)


df = df.sort_values(by=["wl_ratio"], ascending=False)
df.to_html("/home/daniel/trader_stats.html")

for goodtrader in df[:7].iterrows():
    trader_db = ts.get_trader_by_id(goodtrader[1].id)
    trader = Trader(trader_db["id"], trader_db["name"])
    trader.hist = TraderHistory(trader_db["history"])
    trader.hist.show(trader_db["name"])

