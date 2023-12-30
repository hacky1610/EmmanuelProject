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
client = pymongo.MongoClient(f"mongodb+srv://emmanuel:qkcGMAdpjKF1I7Jw@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ms = MarketStore(db)
ds = DealStore(db, "DEMO")
analytics = Analytics(ms)
trade_type = TradeType.FX

viewer = BaseViewer()
only_one_position = True


# endregion

# region functions
def evaluate_predictor(indicators, ig: IG, ti: Tiingo, predictor_class, viewer: BaseViewer, only_one_position: bool = True,
                       only_test=False, predictor_settings:Dict = {}):
    global symbol
    results = EvalResultCollection()
    markets = ig.get_markets(tradeable=False, trade_type=trade_type)
    # for m in random.choices(markets,k=30):
    for m in markets:
        try:
            symbol = m["symbol"]
            #symbol = "EURCZK"
            df, df_eval = ti.load_test_data(symbol, dp, trade_type)

            if len(df) > 0:
                predictor = predictor_class(indicators=indicators, cache=df_cache, viewer=viewer)
                predictor.load(symbol)
                predictor.setup(predictor_settings)
                ev_result = analytics.evaluate(predictor=predictor,
                                               df=df,
                                               df_eval=df_eval,
                                               viewer=viewer,
                                               symbol=symbol,
                                               only_one_position=only_one_position,
                                               scaling=m["scaling"])

                predictor.set_result(ev_result)
                results.add(ev_result)
                if not only_test:
                    predictor.save(symbol)
                viewer.save(symbol)
                print(f"{symbol} - {ev_result}")
        except:
            print("error")
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