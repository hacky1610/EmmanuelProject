from pandas import DataFrame
from BL import ConfigReader
from Connectors.deal_store import DealStore
from Connectors.market_store import MarketStore
from Connectors.trader_store import TraderStore
import pymongo

conf_reader = ConfigReader("DEMO")
client = pymongo.MongoClient(f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")

db = client["ZuluDB"]
ts = TraderStore(db)
df = DataFrame()
ms = MarketStore(db)
ds = DealStore(db,"LIVE")

for trader in ts.get_all_traders():
    try:
        print(f"Analyse {trader.name}")
        if trader.hist.has_history():
            trader.calc_ig(ms)
            ts.save(trader)

    except Exception as ex:
        print(f"Error {ex}")




