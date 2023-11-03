


import time

from selenium import webdriver

from Connectors.trader_store import TraderStore, Trader
from Connectors.zulu_api import ZuluApi
from Tracing.ConsoleTracer import ConsoleTracer
import pymongo

from UI.zulutrade import ZuluTradeUI

# Verbindung zur MongoDB-Datenbank herstellen
client = pymongo.MongoClient("mongodb://localhost:27017")
db = client["ZuluDB"]
ts = TraderStore(db)

zuluUI = ZuluTradeUI(webdriver.Chrome())
for leader in zuluUI.get_leaders():
    trader = Trader(leader["id"], leader["name"])
    ts.add(trader)



print("Updates history")

