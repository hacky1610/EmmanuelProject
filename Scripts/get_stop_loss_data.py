import time

from pandas import DataFrame
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from BL import ConfigReader
from Connectors.IG import IG
from Connectors.tiingo import TradeType
from Connectors.market_store import MarketStore, Market
from Tracing.ConsoleTracer import ConsoleTracer
import pymongo

from UI.fx import FxUi

conf_reader = ConfigReader("DEMO")
# Verbindung zur MongoDB-Datenbank herstellen
client = pymongo.MongoClient(f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")

db = client["ZuluDB"]
options = Options()
#options.add_argument('--headless')
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(options=options, service=service)
driver.implicitly_wait(15)
fx = FxUi(driver)
ms = MarketStore(db)

ig = IG(tracer=ConsoleTracer(True), conf_reader=conf_reader, acount_type="DEMO")
markets = ig.get_markets(TradeType.FX,tradeable=False)

for m in markets:
    try:
        eur_pip =fx.get_stop(m["symbol"])
        m = Market(m["symbol"],eur_pip)
        ms.save(m)
    except Exception as ex:
        print(f"{m['symbol']} error")


