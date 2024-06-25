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
client = pymongo.MongoClient(
    f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ms = MarketStore(db)
ps = PredictorStore(db)
an = Analytics(market_store=ms, ig=IG(conf_reader=conf_reader))
_trainer = Trainer(analytics=an,
                   cache=cache,
                   check_trainable=False,
                   predictor_store=ps)
_tiingo = Tiingo(conf_reader=conf_reader, cache=cache, tracer=_tracer)
_dp = DataProcessor()
_trade_type = TradeType.FX
_indicators = Indicators()
_reporting = Reporting(predictor_store=ps)


# endregion


def get_train_data(tiingo: Tiingo, symbol: str, trade_type: TradeType, dp: DataProcessor) -> (DataFrame, DataFrame):
    hour_df = f"D:\\tmp\Tiingo\\{symbol}_train_1hour.csv"
    minute_df = f"D:\\tmp\Tiingo\\{symbol}_train_5minute.csv"
    if os.path.exists(hour_df) and os.path.exists(minute_df):
        df_train = pd.read_csv(hour_df)
        eval_df_train = pd.read_csv(minute_df)
    else:
        df_train, eval_df_train = tiingo.load_train_data(symbol, dp, trade_type=trade_type)
        df_train.to_csv(hour_df)
        eval_df_train.to_csv(minute_df)

    return df_train, eval_df_train


def get_test_data(tiingo: Tiingo, symbol: str, trade_type: TradeType, dp: DataProcessor) -> (DataFrame, DataFrame):
    hour_df = f"D:\\tmp\Tiingo\\{symbol}_test_1hour.csv"
    minute_df = f"D:\\tmp\Tiingo\\{symbol}_test_5minute.csv"
    if os.path.exists(hour_df) and os.path.exists(minute_df):
        df_train = pd.read_csv(hour_df)
        eval_df_train = pd.read_csv(minute_df)
    else:
        df_train, eval_df_train = tiingo.load_test_data(symbol, dp, trade_type=trade_type)
        df_train.to_csv(hour_df)
        eval_df_train.to_csv(minute_df)

    return df_train, eval_df_train


def get_best_combo(symbol: str):
    path = f"D:\\tmp\\BestCombo\\{symbol}.txt"

    if not os.path.exists(path):
        return ["rsi"]

    with open(path, "r") as datei:
        gelesene_liste = datei.readlines()

    # Zeilenenden entfernen
    gelesene_liste = [element.strip() for element in gelesene_liste]
    return gelesene_liste


def save_best_combo(symbol: str, best_combo: []):
    if best_combo is None:
        return

    path = f"D:\\tmp\\BestCombo\\{symbol}.txt"

    with open(path, "w") as datei:
        for element in best_combo:
            datei.write(element + "\n")


def train_predictor(markets: list,
                    trainer: Trainer,
                    tiingo: Tiingo,
                    dp: DataProcessor,
                    predictor: Type,
                    indicators: Indicators,
                    trade_type: TradeType = TradeType.FX,
                    tracer=ConsoleTracer()
                    ):
    tracer.info("Start training")

    for m in random.choices(markets, k=10):
        symbol = m["symbol"]
        tracer.info(f"Matrix Train {symbol}")
        df_train, eval_df_train = get_train_data(tiingo, symbol, trade_type, dp)
        df_test, eval_df_test = get_test_data(tiingo, symbol, trade_type, dp)

        if len(df_train) > 0:
            try:
                config = ps.load_active_by_symbol(symbol)

                pred_standard = GenericPredictor(symbol=symbol, indicators=indicators)
                pred_standard.setup(config)
                pred_matrix = GenericPredictor(symbol=symbol, indicators=indicators)
                pred_matrix.setup(config)

                trainer.get_signals(symbol, df_train, indicators, predictor)
                buy_results, sell_results = trainer.simulate(df_train, eval_df_train, symbol, m["scaling"], config)
                best_combo = trainer.foo_combinations(symbol, indicators, get_best_combo(symbol),
                                                      pred_standard._indicator_names, buy_results, sell_results)
                if best_combo is None or len(best_combo) == 0:
                    print("No best combo found")
                    continue
                save_best_combo(symbol, best_combo)


                pred_matrix.setup({"_indicator_names": best_combo})

                pred_matrix.eval(df_test, eval_df_test, analytics=an, symbol=symbol, scaling=m["scaling"])

                pred_standard.eval(df_test, eval_df_test, analytics=an, symbol=symbol, scaling=m["scaling"])

                if pred_matrix.get_result().get_reward() > pred_standard.get_result().get_reward():
                    pred_matrix.activate()
                    ps.save(pred_matrix)
                    print(f"****************************************")
                    print(f"* Matrix is better {symbol} {best_combo}")
                    print(f"* Matrix Train {pred_matrix.get_result().get_reward()} - {pred_matrix.get_result()}")
                    print(f"* Standard Train {pred_standard.get_result().get_reward()} - {pred_standard.get_result()}")
                    print(f"****************************************")

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
                        tracer=_tracer)
    except Exception as ex:
        traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
        print(f"MainException: {ex} File:{traceback_str}")
