import time

from selenium import webdriver
from Connectors.trader_store import TraderStore, Trader
from Connectors.zulu_api import ZuluApi
from Tracing.ConsoleTracer import ConsoleTracer
from UI.zulutrade import ZuluTradeUI
import pymongo

# Verbindung zur MongoDB-Datenbank herstellen
client = pymongo.MongoClient("mongodb://localhost:27017")
db = client["ZuluDB"]


ts = TraderStore(db)
ts.add(Trader(id="424537",
              name="SwissWay"))




