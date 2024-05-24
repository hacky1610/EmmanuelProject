# region import
import random
from typing import Dict

import pymongo

from BL import DataProcessor,  ConfigReader
from BL.analytics import Analytics
from BL.eval_result import  EvalResultCollection

from Connectors.IG import IG
from Connectors.deal_store import DealStore
from Connectors.dropbox_cache import DropBoxCache
from Connectors.dropboxservice import DropBoxService
from Connectors.market_store import MarketStore
from Connectors.tiingo import Tiingo, TradeType
from Predictors.chart_pattern_rectangle import RectanglePredictor
from Predictors.chart_pattern_triangle import TrianglePredictor
from Predictors.generic_predictor import GenericPredictor
from Predictors.ichi_predictor import IchimokuPredictor
from UI.plotly_viewer import PlotlyViewer
from UI.base_viewer import BaseViewer
from BL.indicators import Indicators
import dropbox

# endregion

# region static members
conf_reader = ConfigReader()
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx, "DEMO")
df_cache = DropBoxCache(ds)
dp = DataProcessor()
ig = IG(conf_reader)
ti = Tiingo(conf_reader=conf_reader, cache=df_cache)
indicators = Indicators()
client = pymongo.MongoClient(f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ms = MarketStore(db)
ds = DealStore(db, "DEMO")
analytics = Analytics(ms)
trade_type = TradeType.FX

only_one_position = True


# endregion

# region functions
def find_bad_indicators(indicators, ig: IG,predictor_class):
    global symbol
    results = EvalResultCollection()
    markets = ig.get_markets(tradeable=False, trade_type=trade_type)
    good_indicators = []
    for m in markets:
        try:
            predictor = predictor_class(indicators=indicators, cache=df_cache)
            predictor.load(m["symbol"])

            wl = predictor.get_last_result().get_win_loss()
            if wl > 0.6:
                good_indicators.append(predictor.self._indicator_names)


        except:
            print("error")
    print(f"{results}")


# endregion

find_bad_indicators(indicators,ig,GenericPredictor)

