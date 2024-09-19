# region import
import random
import traceback
from typing import Dict

import pymongo
from pandas import DataFrame

from BL import DataProcessor, ConfigReader, measure_time
from BL.analytics import Analytics
from BL.eval_result import EvalResultCollection, EvalResult

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
client = pymongo.MongoClient(
    f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ms = MarketStore(db)
ds = DealStore(db, "DEMO")
analytics = Analytics(ms, ig)
trade_type = TradeType.FX
ps = PredictorStore(db)
_viewer = BaseViewer()


# endregion

# region functions
def get_test_data(tiingo: Tiingo, symbol: str, trade_type: TradeType, dp: DataProcessor,
                  dropbox_cache: DropBoxCache) -> (DataFrame, DataFrame):
    hour_df = f"{symbol}_test_1hour.csv"
    minute_df = f"{symbol}_test_5minute.csv"

    if dropbox_cache.train_cache_exist(hour_df) and dropbox_cache.train_cache_exist(minute_df):
        df_train = dropbox_cache.load_train_cache(hour_df)
        eval_df_train = dropbox_cache.load_train_cache(minute_df)

        if "PIVOT" not in df_train.columns:
            from finta import TA
            pivot = TA.PIVOT(df_train)
            df_train["PIVOT"] = pivot["pivot"]
            df_train["S1"] = pivot["s1"]
            df_train["S2"] = pivot["s2"]
            df_train["R1"] = pivot["r1"]
            df_train["R2"] = pivot["r2"]

        if "PIVOT_FIB" not in df_train.columns:
            from finta import TA
            pivot = TA.PIVOT_FIB(df_train)
            df_train["PIVOT_FIB"] = pivot["pivot"]
            df_train["S1_FIB"] = pivot["s1"]
            df_train["S2_FIB"] = pivot["s2"]
            df_train["R1_FIB"] = pivot["r1"]
            df_train["R2_FIB"] = pivot["r2"]

    else:
        df_train, eval_df_train = tiingo.load_test_data(symbol, dp, trade_type=trade_type)
        dropbox_cache.save_train_cache(df_train, hour_df)
        dropbox_cache.save_train_cache(eval_df_train, minute_df)

    return df_train, eval_df_train


def get_train_data(tiingo: Tiingo, symbol: str, trade_type: TradeType, dp: DataProcessor,
                   dropbox_cache: DropBoxCache) -> (DataFrame, DataFrame):
    hour_df = f"{symbol}_train_1hour.csv"
    minute_df = f"{symbol}_train_5minute.csv"

    if dropbox_cache.train_cache_exist(hour_df) and dropbox_cache.train_cache_exist(minute_df):
        df_train = dropbox_cache.load_train_cache(hour_df)
        eval_df_train = dropbox_cache.load_train_cache(minute_df)

        if "PIVOT" not in df_train.columns:
            from finta import TA
            pivot = TA.PIVOT(df_train)
            df_train["PIVOT"] = pivot["pivot"]
            df_train["S1"] = pivot["s1"]
            df_train["S2"] = pivot["s2"]
            df_train["R1"] = pivot["r1"]
            df_train["R2"] = pivot["r2"]

        if "PIVOT_FIB" not in df_train.columns:
            from finta import TA
            pivot = TA.PIVOT_FIB(df_train)
            df_train["PIVOT_FIB"] = pivot["pivot"]
            df_train["S1_FIB"] = pivot["s1"]
            df_train["S2_FIB"] = pivot["s2"]
            df_train["R1_FIB"] = pivot["r1"]
            df_train["R2_FIB"] = pivot["r2"]
    else:
        df_train, eval_df_train = tiingo.load_train_data(symbol, dp, trade_type=trade_type)
        dropbox_cache.save_train_cache(df_train, hour_df)
        dropbox_cache.save_train_cache(eval_df_train, minute_df)

    return df_train, eval_df_train



def evaluate_predictor(symbol: str, epic: str, scaling: int, indicator_logic: Indicators, viewer: BaseViewer,
                       only_one_position: bool = False, only_test=True) -> EvalResult:
    df, df_eval = get_test_data(ti, symbol, trade_type, dp, dropbox_cache=df_cache)
    indicators.reset_caches()

    if len(df) > 0:
        predictor: BasePredictor = GenericPredictor(symbol=symbol, indicators=indicator_logic, viewer=viewer)
        predictor.setup(ps.load_active_by_symbol(symbol))
        predictor.eval(df_train=df, df_eval=df_eval,
                       only_one_position=only_one_position, analytics=analytics,
                       symbol=symbol, scaling=scaling, epic=epic)

        if predictor.get_result() is None:
            return None

        if not only_test:
            predictor.activate()
            ps.save(predictor)

        viewer.init(predictor.get_result().get_reward(), df, df_eval)
        viewer.print_graph()
        for r in predictor.get_result().get_trade_results():
            viewer.print_trade_result(r, df)
        viewer.show()

        gb = "BAD"
        if predictor.get_result().is_good():
            gb = f"GOOD {predictor}"

        print(f"{gb} - {symbol} - {predictor.get_result()} {predictor} ISL Adapted {predictor.get_result()._adapted_isl_distance}")
        return predictor.get_result()
    return None



def evaluate_predictors(indicator_logic,
                        viewer: BaseViewer,
                        only_one_position: bool = True,
                        only_test=False):
    results = EvalResultCollection()
    markets = IG.get_markets_offline()
    for m in markets:
        #if m["symbol"] != "AUDCHF":
        #    continue
        results.add(evaluate_predictor(m["symbol"],
                                       m["epic"],
                                       m["scaling"],
                                       indicator_logic,
                                       viewer,
                                       only_one_position, only_test)
                    )

    print(f"{results}")


# endregion

#_viewer = PlotlyViewer(cache=df_cache)

evaluate_predictors(indicators,
                    _viewer,
                    only_test=False,
                    only_one_position=False)
