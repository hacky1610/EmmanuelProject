# region import
import time

import pymongo
from BL import  ConfigReader
from BL.eval_result import  EvalResultCollection
from Connectors.IG import IG
from Connectors.predictore_store import PredictorStore
from Predictors.generic_predictor import GenericPredictor
from UI.base_viewer import BaseViewer
from BL.indicators import Indicators
# endregion

# region static members
conf_reader = ConfigReader()
indicators = Indicators()
client = pymongo.MongoClient(f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ps = PredictorStore(db)
viewer = BaseViewer()
ig = IG(conf_reader)
# endregion

# region functions
def get_min_stop_dist(indicators,predictor_class, viewer: BaseViewer):
    markets = IG.get_markets_offline()
    for m in markets:

        m["min_stop_disance"] = ig.get_min_stop_distance_online(m["epic"])
        time.sleep(60)

    IG.set_markets_offline(markets)


# endregion


get_min_stop_dist(indicators,
                   GenericPredictor,
                   viewer)