# region import
import os
import random
import traceback
from itertools import combinations
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
from Predictors.matrix_trainer import MatrixTrainer
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
client = pymongo.MongoClient(
    f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ms = MarketStore(db)
ps = PredictorStore(db)
an = Analytics(market_store=ms, ig=IG(conf_reader=conf_reader))
_trainer = MatrixTrainer(analytics=an,
                   cache=cache,
                   check_trainable=False,
                   predictor_store=ps)
_tiingo = Tiingo(conf_reader=conf_reader, cache=cache, tracer=_tracer)
_dp = DataProcessor()
_trade_type = TradeType.FX
_indicators = Indicators()
_reporting = Reporting(predictor_store=ps)


# endregion


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


def train_predictor(markets: list,
                    trainer: MatrixTrainer,
                    tiingo: Tiingo,
                    dp: DataProcessor,
                    predictor: Type,
                    indicators: Indicators,
                    reporting: Reporting,
                    trade_type: TradeType = TradeType.FX,
                    tracer=ConsoleTracer()
                    ):
    tracer.info("Start training")

    for m in random.choices(markets, k=10):
        symbol = m["symbol"]

        tracer.info(f"Matrix Train {symbol}")
        df_train, eval_df_train = get_test_data(tiingo, symbol, trade_type, dp,dropbox_cache=cache)
        df_test, eval_df_test = get_test_data(tiingo, symbol, trade_type, dp, dropbox_cache=cache)

        if len(df_train) == 0:
            continue

        _reporting.create(markets, predictor)
        best_indicator_combos = reporting.get_best_indicator_combos()
        random_best_combos = [list(kombi) for kombi in combinations(reporting.get_best_indicator_names(), 5)]
        random_all_combos = [list(kombi) for kombi in combinations(indicators.get_all_indicator_names(), 5)]
        all_combos = random_all_combos + random_best_combos

        if len(df_train) > 0:
            try:
                config = ps.load_active_by_symbol(symbol)

                pred_standard = GenericPredictor(symbol=symbol, indicators=indicators)
                pred_standard.setup(config)
                if pred_standard.get_result().get_win_loss() < 0.3:
                   print(f"Skip {symbol} {pred_standard.get_result().get_win_loss() }")
                   continue
                pred_matrix = GenericPredictor(symbol=symbol, indicators=indicators)
                pred_matrix.setup(config)

                trainer.get_signals(symbol, df_train, indicators, predictor)
                buy_results, sell_results = trainer.simulate(df_train, eval_df_train, symbol, m["scaling"], config, epic=m["epic"])

                buy_results_dict = {}
                sell_results_dict = {}
                if len(buy_results) > 0:
                    buy_results_dict = buy_results.set_index('chart_index').to_dict(orient='index')
                    if buy_results['next_index'].nunique() < 4:
                        print(f"Extrem wenige werte {buy_results}")

                if len(sell_results) > 0:
                    sell_results_dict = sell_results.set_index('chart_index').to_dict(orient='index')
                    if sell_results['next_index'].nunique() < 4:
                        print(f"Extrem wenige werte {sell_results}")


                filtered_combos = random.choices(all_combos,k=20000)
                best_combo = trainer.train_combinations(symbol=symbol, indicators=indicators, best_combo_list=best_indicator_combos,
                                                        buy_results=buy_results_dict, sell_results=sell_results_dict, random_combos=filtered_combos)
                if best_combo is None or len(best_combo) == 0:
                    print("No best combo found")
                    continue

                if sorted(best_combo) == sorted(pred_standard.get_indicator_names()):
                    print("Best indicator is equal to standard")
                    continue

                pred_matrix.setup({"_indicator_names": best_combo})
                pred_matrix.eval(df_test, eval_df_test, analytics=an, symbol=symbol, scaling=m["scaling"], only_one_position=False, epic=m["epic"])
                pred_standard.eval(df_test, eval_df_test, analytics=an, symbol=symbol, scaling=m["scaling"], only_one_position=False, epic=m["epic"])

                if pred_standard.get_result().is_better(pred_matrix.get_result()):
                    pred_matrix.activate()
                    ps.save(pred_matrix)
                    print(f"****************************************")
                    print(f"* Matrix is better {symbol} {best_combo}")
                    print(f"* Matrix Train {pred_matrix.get_result().get_reward()} - {pred_matrix.get_result()}")
                    print(f"* Standard Train {pred_standard.get_result().get_reward()} - {pred_standard.get_result()}")
                    print(f"****************************************")
                else:
                    print("Standard is better")
                    print(f"* Standard Train {pred_standard.get_result().get_reward()} - {pred_standard.get_result()}")
                    pred_standard.activate()
                    ps.save(pred_standard)

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
                        indicators=_indicators,
                        tracer=_tracer,
                        reporting=_reporting)
    except Exception as ex:
        traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
        print(f"MainException: {ex} File:{traceback_str}")
