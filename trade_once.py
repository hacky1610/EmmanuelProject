import pymongo

from BL.analytics import Analytics
from BL.indicators import Indicators
from Connectors.deal_store import DealStore
from Connectors.dropbox_cache import DropBoxCache
from Connectors.dropboxservice import DropBoxService
from Connectors.market_store import MarketStore
from Connectors.tiingo import TradeType, Tiingo
from Predictors.generic_predictor import GenericPredictor
from Tracing.LogglyTracer import LogglyTracer
from Connectors.IG import IG
from BL import EnvReader, DataProcessor
from BL.trader import Trader
import dropbox

env_reader = EnvReader()
type_ = env_reader.get("Type")

if type_ == "DEMO":
    live = False
else:
    live = True

dataProcessor = DataProcessor()
dbx = dropbox.Dropbox(env_reader.get("dropbox"))
ds = DropBoxService(dbx,"DEMO")
cache = DropBoxCache(ds)
tracer = LogglyTracer(env_reader.get("loggly_api_key"), type_, "trade_job")
tiingo = Tiingo(tracer=tracer, conf_reader=env_reader, cache=cache)
ig = IG(conf_reader=env_reader, tracer=tracer, live=live)
predictor_class_list = [GenericPredictor]
client = pymongo.MongoClient(f"mongodb+srv://emmanuel:{env_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ms = MarketStore(db)
ds = DealStore(db, type_)
analytics = Analytics(ms, tracer)
indicators = Indicators(tracer=tracer)

trader = Trader(
    ig=ig,
    tiingo=tiingo,
    tracer=tracer,
    predictor_class_list=predictor_class_list,
    dataprocessor=dataProcessor,
    analytics=analytics,
    cache=cache,
    deal_storage=ds,
    market_storage=ms
)

trader.trade_markets(TradeType.FX, indicators)


