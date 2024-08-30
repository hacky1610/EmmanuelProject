# region import
import random
import traceback
from datetime import datetime, timedelta
from typing import Dict

import pymongo
from pandas import DataFrame

from BL import DataProcessor, ConfigReader
from BL.analytics import Analytics
from BL.datatypes import TradeAction
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
ds = DealStore(db, "LIVE")
analytics = Analytics(ms, ig)
trade_type = TradeType.FX
ps = PredictorStore(db)
viewer = BaseViewer()


# endregion

# region functions
def get_test_data(tiingo: Tiingo, symbol: str, trade_type: TradeType, dp: DataProcessor,  dropbox_cache:DropBoxCache) -> (DataFrame, DataFrame):
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

def get_train_data(tiingo: Tiingo, symbol: str, trade_type: TradeType, dp: DataProcessor, dropbox_cache:DropBoxCache) -> (DataFrame, DataFrame):
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
        dropbox_cache.save_train_cache(df_train,hour_df)
        dropbox_cache.save_train_cache(eval_df_train,minute_df)

    return df_train, eval_df_train

def round(timestamp_str):

    # String in datetime-Objekt umwandeln
    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%fZ')

    # Prüfen, ob Minuten oder Sekunden größer als Null sind
    if timestamp.minute > 0 or timestamp.second > 0 or timestamp.microsecond > 0:
        # Auf die nächste Stunde aufrunden
        timestamp = timestamp.replace(minute=0, second=0, microsecond=0)

    # Ergebnis zurück in einen String konvertieren
    return timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-4] + 'Z'

def convert_string(time_string):

    # String in datetime-Objekt umwandeln
    timestamp = datetime.strptime(time_string, '%Y-%m-%dT%H:%M:%S')

    # Ergebnis in das gewünschte Format konvertieren
    return timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

def round_datetime(timestamp):
    # Minuten und Sekunden auf null setzen
    timestamp = timestamp.replace(minute=0, second=0, microsecond=0)

    # Ergebnis in das gewünschte Format konvertieren
    return timestamp.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'



def evaluate_predictor(indicator_logic, ig: IG, ti: Tiingo, predictor_class, viewer: BaseViewer,
                       only_one_position: bool = True,
                       only_test=False):
    global symbol


    results = EvalResultCollection()
    markets = IG.get_markets_offline()
    for m in markets:
        try:
            symbol = m["symbol"]
            if symbol != "AUDCHF":
                continue

            df, df_eval = ti.load_test_data(symbol=symbol, dp=dp, days=60,trade_type=TradeType.FX ,use_cache=True)

            if len(df) > 0:
                predictor:BasePredictor = predictor_class(symbol=symbol, indicators=indicator_logic, viewer=viewer)
                predictor.setup(ps.load_active_by_symbol(symbol))



                predictor.eval(df_train=df, df_eval=df_eval,
                               only_one_position=only_one_position, analytics=analytics,
                               symbol=symbol, scaling=m["scaling"])

                if predictor.get_result() is None:
                    continue

                viewer.init(predictor.get_result().get_reward(), df, df_eval)
                viewer.print_graph()

                for r in predictor.get_result().get_trade_results():
                    try:
                        if r.action == TradeAction.BUY:
                            viewer.print_buy(df[df.date == r.open_time].index.item(),r.opening, add_text=str(r))
                        else:
                            viewer.print_sell(df[df.date == r.open_time].index.item(),r.opening, add_text=str(r))

                        close_time = round(r.close_time)
                        if r.profit < 0:
                            viewer.print_lost(df[df.date == close_time].index.item(),r.closing)
                        else:
                            viewer.print_won(df[df.date == close_time].index.item(), r.closing)
                    except Exception as e:
                        print(e)

                deals = ds.get_closed_deals_by_ticker(symbol)
                for d in deals:
                    try:
                        atr = df.iloc[-1].ATR
                        open_time = round(convert_string(d.open_date_ig_str))
                        if d.direction == "buy":
                            viewer.print_buy_2(df[df.date == open_time].index.item(), d.open_level + atr, add_text=str(d))
                        else:
                            viewer.print_sell_2(df[df.date == open_time].index.item(), d.open_level + atr, add_text=str(d))

                        close_time = round_datetime(d.close_date_ig_datetime)
                        if d.profit > 0:
                            viewer.print_won_2(df[df.date == close_time].index.item(), d.close_level + atr)
                        else:
                            viewer.print_lost_2(df[df.date == close_time].index.item(), d.close_level + atr)
                    except Exception as e:
                        print(e)

                viewer.show()




                results.add(predictor.get_result())
                if not only_test:
                    predictor.activate()
                    ps.save(predictor)
                viewer.save(symbol)
                gb = "BAD"
                if predictor.get_result().is_good():
                    gb = f"GOOD {predictor}"

                print(f"{gb} - {symbol} - {predictor.get_result()} {predictor} ")
        except Exception as e:
            traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
            print(f"MainException: {e} File:{traceback_str}")
    print(f"{results}")


# endregion

viewer = PlotlyViewer(cache=df_cache)


evaluate_predictor(indicators,
                   ig,
                   ti,
                   GenericPredictor,
                   viewer,
                   only_test=True,
                   only_one_position=True)
