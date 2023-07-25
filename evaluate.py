# region import
import random
from BL import DataProcessor, Analytics, ConfigReader
from BL.eval_result import EvalResult, EvalResultCollection
from Connectors import Tiingo, TradeType, IG, DropBoxCache, DropBoxService, BaseCache
from Predictors.chart_pattern_rectangle import RectanglePredictor
from Predictors.chart_pattern_triangle import TrianglePredictor
from UI.plotly_viewer import PlotlyViewer
from UI.base_viewer import BaseViewer
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
analytics = Analytics()
trade_type = TradeType.FX
results = EvalResultCollection()
viewer = BaseViewer()


# endregion

# region functions
def evaluate_predictor(ig: IG, ti: Tiingo, predictor_class, viewer: BaseViewer, only_one_position: bool = True,
                       only_test=False):
    global symbol
    markets = ig.get_markets(tradeable=False, trade_type=trade_type)
    # for m in random.choices(markets,k=30):
    for m in markets:
        symbol = m["symbol"]
        #symbol = "AUDUSD"
        df, df_eval = ti.load_train_data(symbol, dp, trade_type)

        if len(df) > 0:
            predictor = predictor_class(cache=df_cache, viewer=viewer)
            predictor.load(symbol)
            ev_result = analytics.evaluate(predictor=predictor,
                                           df_train=df,
                                           df_eval=df_eval,
                                           viewer=viewer,
                                           symbol=symbol,
                                           only_one_position=only_one_position)

            predictor.set_result(ev_result)
            results.add(ev_result)
            if not only_test:
                predictor.save(symbol)
            viewer.save(symbol)
            print(f"{symbol} - {ev_result}")
    print(f"{results}")


# endregion

viewer = PlotlyViewer(cache=df_cache)

evaluate_predictor(ig, ti, RectanglePredictor, viewer)
#evaluate_predictor(ig, ti, TrianglePredictor, viewer)
