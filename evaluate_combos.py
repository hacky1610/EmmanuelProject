# region import
import os
import random
import traceback
import dropbox
import pymongo
import pandas as pd
from pandas import DataFrame

import Data.combos
from BL.Simulation import Simulation
from BL.analytics import Analytics
from BL.combination_trainer import CombinationTrainer
from BL.data_processor import DataProcessor
from BL.datatypes import TradeAction
from BL.indicators import Indicators
from BL.utils import ConfigReader, EnvReader
from Connectors.IG import IG
from Connectors.dropbox_cache import DropBoxCache
from Connectors.dropboxservice import DropBoxService
from Connectors.market_store import MarketStore
from Connectors.predictore_store import PredictorStore
from Connectors.tiingo import TradeType, Tiingo
from Predictors.generic_predictor import GenericPredictor
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
_cache = DropBoxCache(ds)
client = pymongo.MongoClient(
    f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ms = MarketStore(db)
predictor_store = PredictorStore(db)
an = Analytics(market_store=ms, ig=IG(conf_reader=conf_reader))
_simulation = Simulation(_cache, an)
_tiingo = Tiingo(conf_reader=conf_reader, cache=_cache, tracer=_tracer)
_dp = DataProcessor()
_trade_type = TradeType.FX
_indicators = Indicators()
_reporting = Reporting(predictor_store=predictor_store)


# endregion


def train_symbols(markets, simulation, cache, tiingo, data_processor, indicators, trade_type=TradeType.FX,
                  tracer=ConsoleTracer()):
    # General configuration and data processing
    markets = IG.get_markets_offline()
    random.shuffle(markets)
    for market in markets:

        fx = market["symbol"]

        #fx = "NZDUSD"
        indicators.reset_caches()

        #if predictor_store.count_of_all_by_symbol(fx) > 40:
        #    print("Enough training data to train")
        #    continue

        online_combos = Data.combos.get_combos()

        best_features_online_0_5 = predictor_store.get_most_used_features(0.5)
        best_features_online_0_2 = predictor_store.get_most_used_features(0.2)

        hours = 16
        data = random.choice([(1.3,0.5,0.75, 0.7)
                     ])
        atr_factor_stop = data[0]
        atr_factor_limit = data[1]
        minimum_precission_train = data[2]
        minimum_precission_test = data[3]

        combis = [(6, 0.1),
                  (8, 0.1),
                  (7, 0.2),
                  (9, 0.5),
                  (10, 0.3)]

        for combination_size_tuple in random.choices(combis,k=3):

            f = 0
            combination_size = combination_size_tuple[0]
            part = combination_size_tuple[1]
            for features in [best_features_online_0_5,
                             best_features_online_0_2,
                             random.choices( indicators.get_all_indicator_names(), k=25)]:
                f += 1
                ct = CombinationTrainer(cache=cache,
                                        indicators=indicators,
                                        predictor_store=predictor_store,
                                        test_mode=True)
                try:

                    for trade_action in [TradeAction.SELL,TradeAction.BUY]:
                        print(
                            f"Evaluate {fx} {trade_action} for {hours} hours and stop factor "
                            f"{atr_factor_stop} limit {atr_factor_limit} and min prec {minimum_precission_train} combination {combination_size} Feature Set {f}")
                        df_train_global = ct.create_data(tiingo=tiingo, symbol=fx,
                                                         trade_type=trade_type, data_processor=data_processor,
                                                         simulation=simulation, hours=hours,
                                                         factor_stop=atr_factor_stop, factor_limit=atr_factor_limit,
                                                         indicators=indicators,
                                                         trade_mode=trade_action, cache=cache)

                        ct.train(df=df_train_global,
                                 trading_hours=hours,
                                 min_prec_train=minimum_precission_train,
                                 num_features=combination_size,
                                 trading_mode=trade_action,
                                 symbol=fx,
                                 atr_factor_stop=atr_factor_stop,
                                 atr_factor_limit=atr_factor_limit,
                                 best_features=features, min_prec_test=minimum_precission_test,
                                 part=part,existing_combos=online_combos)

                except Exception as ex:
                    traceback_str = traceback.format_exc()
                    print(f"MainException: {ex} File:{traceback_str}")


while True:
    try:
        train_symbols(markets=IG.get_markets_offline(),
                      tiingo=_tiingo,
                      data_processor=_dp,
                      indicators=_indicators,
                      tracer=_tracer,
                      cache=_cache,
                      simulation=_simulation)
    except Exception as ex:
        traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
        print(f"MainException: {ex} File:{traceback_str}")
