# region import
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
# endregion

# region functions
def evaluate_predictor(indicators,predictor_class, viewer: BaseViewer):
    global symbol
    results = EvalResultCollection()
    markets = IG.get_markets_offline()
    for m in markets:
        try:
            symbol = m["symbol"]

            predictor = predictor_class(indicators=indicators, symbol=symbol, viewer=viewer)
            predictor.setup(ps.load_active_by_symbol(symbol))

            gb = "BAD"
            if predictor.get_result().is_good():
                gb = f"GOOD"

            print(f"{gb} - {symbol} - {predictor.get_result()}")
        except:
            print("error")
    print(f"{results}")
# endregion


evaluate_predictor(indicators,
                   GenericPredictor,
                   viewer)