import datetime
# region import
import json
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
ps = PredictorStore(db, account_type)
_trainer = Trainer(analytics=Analytics(market_store=ms),
                   cache=cache,
                   check_trainable=False,
                   predictor_store=ps)
_tiingo = Tiingo(conf_reader=conf_reader, cache=cache, tracer=_tracer)
_dp = DataProcessor()
_trade_type = TradeType.FX
_ig = IG(conf_reader=conf_reader, live=live, tracer=_tracer)
_indicators = Indicators()
_reporting = Reporting(predictor_store=ps)
# endregion



def _get_filename(symbol):
    return f"GenericPredictor_{symbol}V3.0.json"

def load(symbol: str):
    json = cache.load_settings(_get_filename(symbol))

    return json


with open(os.path.join("Data", "markets.json"), 'r') as json_file:
    markets = json.load(json_file)

for m in markets:

    js = load(m["symbol"])
    g = GenericPredictor(symbol=m["symbol"],indicators=_indicators)
    g.setup(js)
    g.activate()
    g.get_result()._scan_time = datetime.datetime.now()
    ps.save(g)