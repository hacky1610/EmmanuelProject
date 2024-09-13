# region import
import os
import random
import traceback
from typing import Type

import dropbox
import pymongo
import pandas as pd
from pandas import DataFrame

from BL.analytics import Analytics
from BL.data_processor import DataProcessor
from BL.indicators import Indicators
from BL.utils import ConfigReader, EnvReader
from Connectors.IG import IG
from Connectors.dropbox_cache import DropBoxCache
from Connectors.dropboxservice import DropBoxService
from Connectors.market_store import MarketStore
from Connectors.predictore_store import PredictorStore
from Connectors.tiingo import TradeType, Tiingo
from Predictors.generic_predictor import GenericPredictor
from Predictors.trainer import Trainer
from Predictors.utils import Reporting
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.LogglyTracer import LogglyTracer

# endregion

type_ = "DEMO"
if type_ == "DEMO":
    live = False
else:
    live = True

# region statics
if os.name == 'nt' or os.environ.get("USER", "") == "daniel":
    account_type = "DEMO"
    conf_reader = ConfigReader(False)
    _tracer = ConsoleTracer()
else:
    conf_reader = EnvReader()
    account_type = conf_reader.get("Type")
    _tracer = LogglyTracer(conf_reader.get("loggly_api_key"), type_, "train_job")




dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx, type_)
cache = DropBoxCache(ds)
client = pymongo.MongoClient(f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ms = MarketStore(db)
ps = PredictorStore(db)
_trainer = Trainer(analytics=Analytics(market_store=ms, ig=IG(conf_reader=conf_reader)),
                   cache=cache,
                   check_trainable=False,
                   predictor_store=ps)
_tiingo = Tiingo(conf_reader=conf_reader, cache=cache, tracer=_tracer)
_dp = DataProcessor()
_trade_type = TradeType.FX
_indicators = Indicators()
_reporting = Reporting(predictor_store=ps)
# endregion

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

def train_predictor(markets:list,
                    trainer: Trainer,
                    tiingo: Tiingo,
                    dp: DataProcessor,
                    predictor: Type,
                    indicators: Indicators,
                    reporting:Reporting,
                    trade_type: TradeType = TradeType.FX,
                    tracer = ConsoleTracer()
                    ):
    tracer.info("Start training")
    reporting.create(markets, predictor)
    best_indicators = reporting.get_best_indicator_names()
    best_indicator_combos = reporting.get_best_indicator_combos()
    tracer.info(f"Best indicators: {best_indicators}")

    if len(best_indicators) == 0:
        best_indicators.append("RSI")
    random.shuffle(markets)

    for m in markets:
        # for m in markets:
        symbol = m["symbol"]


        tracer.info(f"Train {symbol}")
        df_train, eval_df_train = get_test_data(tiingo, symbol, trade_type, dp, dropbox_cache=cache)
        df_test, eval_df_test = get_test_data(tiingo, symbol, trade_type, dp, dropbox_cache=cache)
        if len(df_train) > 0:
            try:
                p = GenericPredictor(indicators=indicators, symbol=symbol)
                p.setup(ps.load_best_by_symbol(symbol))
                if p.get_result().get_win_loss() < 0.66:
                    print(f"Skip {symbol} - WL to low {p.get_result().get_win_loss() }")
                    continue
                print(f"{symbol} - Current WL {p.get_result().get_win_loss()}")
                trainer.train(symbol, m["epic"],  m["scaling"], df_train, eval_df_train,df_test, eval_df_test, predictor, indicators, best_indicators,
                              best_online_config=ps.load_best_by_symbol(symbol), best_indicator_combos=best_indicator_combos)
            except Exception as ex:
                traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
                print(f"MainException: {ex} File:{traceback_str}")

        else:
            print(f"No Data in {symbol} ")


while True:
    try:
        train_predictor(markets=IG.get_markets_offline(),
                        trainer=_trainer,
                        tiingo=_tiingo,
                        predictor=GenericPredictor,
                        dp=_dp,
                        reporting=_reporting,
                        indicators=_indicators,
                        tracer=_tracer)
    except Exception as e:
        traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
        print(f"MainException: {e} File:{traceback_str}")


