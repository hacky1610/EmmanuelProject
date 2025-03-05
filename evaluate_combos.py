# region import
import os
import random
import traceback
import dropbox
import pymongo
import pandas as pd
from pandas import DataFrame
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
        fx = "EURSEK"
        indicators.reset_caches()

        #if predictor_store.count_of_all_by_symbol(fx) > 40:
        #    print("Enough training data to train")
        #    continue

        best_features = predictor_store.get_most_used_features()
        best_features = [
            "rsi_convergence", "macd_convergence", "williams_break_4h", "rsi_break_4h",
            "macd_max_4h", "bb_sqeeze_both_direction_4h", "bb_middle_crossing_4h",
            "macd_max", "adx_max_4h", "rsi", "adx_max", "adx_max2",
            "bb_sqeeze_both_direction", "macd_max_12h", "adx_max_21", "adx",
            "macd", "macd_slope_4h", "rsi_limit_12h", "adx_max_48",
            "rsi_limit_4h", "ema_10_50", "cci_4h", "williams_limit_4h",
            "adx_4h", "rsi_convergence5_40"
        ]

        for hours in [16]:
            for factor in [2.0]:
                combination_size = 4
                quantile = 0.7
                ct = CombinationTrainer(cache=cache,
                                        indicators=indicators,
                                        predictor_store=predictor_store,
                                        test_mode=True)
                try:
                    print(
                        f"Evaluate {fx}  for {hours} hours and factor {factor} and quantille {quantile} combination {combination_size}")

                    for trade_action in [TradeAction.BUY, TradeAction.SELL]:
                        df_train_global  = ct.create_data(tiingo, fx,
                                                                  trade_type, data_processor,
                                                                  simulation, hours,
                                                                  factor, indicators,
                                                                  trade_action, cache)

                        ct.train(df=df_train_global,
                                 trading_hours=hours,
                                 min_prec=quantile,
                                 num_features=combination_size,
                                 trading_mode=trade_action,
                                 symbol=fx,
                                 atr_factor=factor,
                                 best_features=best_features)

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
