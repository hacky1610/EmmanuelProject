# region import
import random
import traceback
from typing import Dict

import pymongo

from BL import DataProcessor, ConfigReader
from BL.analytics import Analytics
from BL.eval_result import EvalResultCollection

from Connectors.IG import IG
from Connectors.deal_store import DealStore
from Connectors.dropbox_cache import DropBoxCache
from Connectors.dropboxservice import DropBoxService
from Connectors.market_store import MarketStore
from Connectors.predictore_store import PredictorStore
from Connectors.tiingo import Tiingo, TradeType
from Predictors.base_predictor import BasePredictor
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
analytics = Analytics(ms, ig)
trade_type = TradeType.FX
ps = PredictorStore(db)
viewer = BaseViewer()
only_one_position = True


# endregion

# region functions
def evaluate_predictor(indicator_logic, ig: IG, ti: Tiingo, predictor_class, viewer: BaseViewer,
                       only_one_position: bool = True,
                       only_test=False):
    global symbol
    results = EvalResultCollection()
    markets = IG.get_markets_offline()
    for m in markets:
        try:
            symbol = m["symbol"]
            #symbol = "AUDUSD"
            df, df_eval = ti.load_test_data(symbol, dp, trade_type)

            if len(df) > 0:
                predictor:BasePredictor = predictor_class(symbol=symbol, indicators=indicator_logic, viewer=viewer)
                predictor.setup(ps.load_active_by_symbol(symbol))
                predictor.setup(ps.load_best_by_symbol(symbol))
                predictor.eval(df_train=df, df_eval=df_eval,
                               only_one_position=only_one_position, analytics=analytics,
                               symbol=symbol, scaling=m["scaling"])

                if predictor.get_result() is None:
                    continue

                results.add(predictor.get_result())
                if not only_test:
                    predictor.activate()
                    ps.save(predictor)
                viewer.save(symbol)
                gb = "BAD"
                if predictor.get_result().is_good():
                    gb = f"GOOD {predictor._indicator_names}"

                print(f"{gb} - {symbol} - {predictor.get_result()} {predictor} ")
        except Exception as e:
            traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
            print(f"MainException: {e} File:{traceback_str}")
    print(f"{results}")


# endregion

#viewer = PlotlyViewer(cache=df_cache)


evaluate_predictor(indicators,
                   ig,
                   ti,
                   GenericPredictor,
                   viewer,
                   only_test=True,
                   only_one_position=only_one_position)
