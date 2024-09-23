import os
import time

import pymongo

from BL.analytics import Analytics
from BL.indicators import Indicators
from Connectors.deal_store import DealStore
from Connectors.dropbox_cache import DropBoxCache
from Connectors.dropboxservice import DropBoxService
from Connectors.market_store import MarketStore
from Connectors.predictore_store import PredictorStore
from Connectors.tiingo import TradeType, Tiingo
from Predictors.generic_predictor import GenericPredictor
from Tracing.LogglyTracer import LogglyTracer
from Connectors.IG import IG
from BL import EnvReader, DataProcessor, ConfigReader
from BL.trader import Trader
import dropbox

from Tracing.MultiTracer import MultiTracer
from Tracing.StreamTracer import StreamTracer

if os.name == 'nt':
    account_type = "DEMO"
    conf_reader = ConfigReader(False)
else:
    conf_reader = EnvReader()
    account_type = conf_reader.get("Type")


if account_type == "DEMO":
    live = False
else:
    live = True


dataProcessor = DataProcessor()
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx,"DEMO")
cache = DropBoxCache(ds)
loggly_tracer = LogglyTracer(conf_reader.get("loggly_api_key"), account_type, "update_job")
tracer = MultiTracer([loggly_tracer, StreamTracer()])
tiingo = Tiingo(tracer=tracer, conf_reader=conf_reader, cache=cache)
ig = IG(conf_reader=conf_reader, tracer=tracer, live=live)
predictor_class_list = [GenericPredictor]
client = pymongo.MongoClient(f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ms = MarketStore(db)
ds = DealStore(db, account_type)
analytics = Analytics(ms, tracer)
indicators = Indicators(tracer=tracer)
ps = PredictorStore(db)

trader = Trader(
    ig=ig,
    tiingo=tiingo,
    tracer=tracer,
    predictor_class_list=predictor_class_list,
    dataprocessor=dataProcessor,
    analytics=analytics,
    predictor_store=ps,
    deal_storage=ds,
    market_storage=ms
)
tracer.debug(f"Update markets {account_type}")
trader.update_markets()


