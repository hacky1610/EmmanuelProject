from selenium import webdriver
from BL import ConfigReader
from Connectors.trader_store import TraderStore, Trader
from Tracing.ConsoleTracer import ConsoleTracer
import pymongo
from UI.zulutrade import ZuluTradeUI
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# Verbindung zur MongoDB-Datenbank herstellen
conf_reader = ConfigReader("DEMO")
client = pymongo.MongoClient(f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")

db = client["ZuluDB"]
options = Options()
options.add_argument('--headless')
service = Service(ChromeDriverManager().install())
ts = TraderStore(db)
driver = webdriver.Chrome(options=options, service=service)
driver.implicitly_wait(15)
zuluUI = ZuluTradeUI(driver, ConsoleTracer())
for leader in zuluUI.get_leaders():
    trader = Trader(leader["id"], leader["name"],0,0)
    ts.add(trader)



print("Updates history")