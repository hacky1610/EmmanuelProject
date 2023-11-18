from pandas import DataFrame
from Connectors.trader_store import TraderStore
import pymongo

# Verbindung zur MongoDB-Datenbank herstellen
client = pymongo.MongoClient("mongodb://localhost:27017")
db = client["ZuluDB"]


ts = TraderStore(db)
df = DataFrame()

for trader in ts.get_all_traders():
    df = df.append(trader.get_statistic(), ignore_index=True)


df = df.sort_values(by=["wl_ratio"], ascending=False)
df.to_html("/home/daniel/trader_stats.html")



