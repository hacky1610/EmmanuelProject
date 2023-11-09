import pymongo

from Connectors.deal_store import DealStore
from Connectors.trader_store import TraderStore

client = pymongo.MongoClient("mongodb://localhost:27017")
db_local = client["ZuluDB"]
ts_local = TraderStore(db_local)
ds_local = DealStore(db_local)

# Verbindung zur MongoDB-Datenbank herstellen
client = pymongo.MongoClient("mongodb+srv://emmanuel:roCLAuQ6vHtWISk9@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")  # Passen Sie die Verbindungs-URL entsprechend an
db_remote = client["ZuluDB"]
ts_remote = TraderStore(db_remote)
ds_remote = DealStore(db_remote)

for trader in   db_local["TraderStore"].find():
    db_remote["TraderStore"].insert_one(trader)

for deal in db_local["Deals"].find():
    db_remote["Deals"].insert_one(deal)