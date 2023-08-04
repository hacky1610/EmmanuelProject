import dropbox
from Connectors import IG, Tiingo, TradeType, DropBoxService, DropBoxCache
from Predictors.chart_pattern_rectangle import RectanglePredictor
from Predictors.chart_pattern_triangle import TrianglePredictor
from Tracing.LogglyTracer import LogglyTracer
from BL import Analytics, ConfigReader, DataProcessor
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
predictor_class_list = [RectanglePredictor, TrianglePredictor]
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

trader.trade_markets(TradeType.FX)
