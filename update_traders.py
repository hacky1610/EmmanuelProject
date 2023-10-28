from selenium import webdriver
from Connectors.trader_store import TraderStore, Trader
from Connectors.zulu_api import ZuluApi
from UI.zulutrade import ZuluTradeUI
import pymongo

# Verbindung zur MongoDB-Datenbank herstellen
client = pymongo.MongoClient("mongodb://localhost:27017")
db = client["ZuluDB"]


zuluUi = ZuluTradeUI(webdriver.Chrome())
zuluUi.login()
zuluApi = ZuluApi()

ts = TraderStore(db)
for f in zuluUi.get_favorites():
    f.hist = zuluApi.get_history(f.id)
    ts.save(f)

print("Updates history")

