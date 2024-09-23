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
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.LogglyTracer import LogglyTracer
from Connectors.IG import IG
from BL import EnvReader, DataProcessor
from BL.trader import Trader
import dropbox

from Tracing.MultiTracer import MultiTracer
from Tracing.StreamTracer import StreamTracer

env_reader = EnvReader()
type_ = env_reader.get("Type")

if type_ == "DEMO":
    live = False
    check_ig_performance = False
else:
    live = True
    check_ig_performance = True

dataProcessor = DataProcessor()
dbx = dropbox.Dropbox(env_reader.get("dropbox"))
ds = DropBoxService(dbx,"DEMO")
cache = DropBoxCache(ds)
loggly_tracer = LogglyTracer(env_reader.get("loggly_api_key"), type_, "trade_job")
tracer = MultiTracer([loggly_tracer, StreamTracer()])
tiingo = Tiingo(tracer=tracer, conf_reader=env_reader, cache=cache)
ig = IG(conf_reader=env_reader, tracer=tracer, live=live)
predictor_class_list = [GenericPredictor]
client = pymongo.MongoClient(f"mongodb+srv://emmanuel:{env_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ms = MarketStore(db)
ds = DealStore(db, type_)
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
    market_storage=ms,
    check_ig_performance=check_ig_performance
)

trader.trade_markets(TradeType.FX, indicators)


