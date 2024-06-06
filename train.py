# region import
import os
import random
import traceback
from typing import Type

import dropbox
import pymongo

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
_trainer = Trainer(analytics=Analytics(market_store=ms),
                   cache=cache,
                   check_trainable=False,
                   predictor_store=ps)
_tiingo = Tiingo(conf_reader=conf_reader, cache=cache, tracer=_tracer)
_dp = DataProcessor()
_trade_type = TradeType.FX
_indicators = Indicators()
_reporting = Reporting(predictor_store=ps)
# endregion


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
    tracer.info(f"Best indicators: {best_indicators}")

    if len(best_indicators) == 0:
        best_indicators.append("RSI")

    for m in random.choices(markets, k=10):
        # for m in markets:
        symbol = m["symbol"]
        symbol = "EURCHF"
        tracer.info(f"Train {symbol}")
        df_train, eval_df_train = tiingo.load_train_data(symbol, dp, trade_type=trade_type)
        #df_test, eval_df_test = tiingo.load_test_data(symbol, dp, trade_type=trade_type)
        if len(df_train) > 0:
            try:
                #trainer.train_all_indicators(symbol, m["scaling"], df_train, eval_df_train, None, None, predictor, indicators)
                trainer.train_indicator(Indicators.RSI_LIMIT,symbol, m["scaling"], df_train, eval_df_train, predictor, indicators)
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
        print(f"Error {e}")


