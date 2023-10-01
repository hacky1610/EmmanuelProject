import dropbox
from BL.analytics import Analytics
from BL.indicators import Indicators
from Connectors.IG import IG
from Connectors.dropbox_cache import DropBoxCache
from Connectors.dropboxservice import DropBoxService
from Connectors.tiingo import Tiingo, TradeType
from Predictors.generic_predictor import GenericPredictor
from Tracing.LogglyTracer import LogglyTracer
from BL import ConfigReader, DataProcessor
from BL.trader import Trader


type_ = "DEMO"
if type_ == "DEMO":

    live = False
else:
    live = True

#region Definitions
dataProcessor = DataProcessor()
conf_reader = ConfigReader(live_config=live)
tracer = LogglyTracer(conf_reader.get("loggly_api_key"), type_)
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx, type_)
cache = DropBoxCache(ds)
tiingo = Tiingo(tracer=tracer, conf_reader=conf_reader, cache=cache)
ig = IG(tracer=tracer, conf_reader=conf_reader, live=live)
analytics = Analytics(tracer)
predictor_class_list = [GenericPredictor]
indicators = Indicators()
#endregion

trader = Trader(
    ig=ig,
    tiingo=tiingo,
    tracer=tracer,
    predictor_class_list=predictor_class_list,
    dataprocessor=dataProcessor,
    analytics=analytics,
    cache=cache
)

trader.trade_markets(TradeType.FX, indicators)
