# region import
import pymongo
from BL import ConfigReader
from Connectors.predictore_store import PredictorStore
# endregion

# region static members
conf_reader = ConfigReader()
client = pymongo.MongoClient(f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster1.uo3fjln.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ps = PredictorStore(db)


print()


