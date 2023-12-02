from pandas import DataFrame
from BL import ConfigReader
from Connectors.market_store import MarketStore
from Connectors.trader_store import TraderStore
import pymongo

conf_reader = ConfigReader("DEMO")
client = pymongo.MongoClient(f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")

db = client["ZuluDB"]
ts = TraderStore(db)
df = DataFrame()
ms = MarketStore(db)

for trader in ts.get_all_traders():
    try:
        print(f"{trader.name}")
        if trader.hist.has_history():
            trader.calc_ig(ms)
            ts.save(trader)
            stat = trader.get_statistic()
            df = df.append(stat, ignore_index=True)
    except Exception as ex:
        print(f"Error {ex}")


df = df.sort_values(by=["ig_custom"], ascending=False)
df.to_html("/home/daniel/trader_stats_new.html")



