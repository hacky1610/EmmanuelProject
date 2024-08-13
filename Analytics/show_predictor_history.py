# region import
import pymongo
from BL import ConfigReader
from Connectors.predictore_store import PredictorStore
# endregion

# region static members
conf_reader = ConfigReader()
client = pymongo.MongoClient(f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ps = PredictorStore(db)


all = ps.load_all_by_symbol("GBPJPY")


for p in all:
    p['_indicator_names'].sort()
    print(f"{p['_scan_time']} {p['_indicator_names']}")


