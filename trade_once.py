from Predictors.sup_res_candle import SupResCandle
from Tracing.LogglyTracer import LogglyTracer
from Connectors import Tiingo, TradeType,DropBoxCache,IG, DropBoxService
from BL import Analytics, EnvReader, DataProcessor, Trader
from Predictors.trainer import Trainer
from datetime import datetime
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
tracer = LogglyTracer(env_reader.get("loggly_api_key"), type_)
tiingo = Tiingo(tracer=tracer, conf_reader=env_reader, cache=cache)
ig = IG(conf_reader=env_reader, tracer=tracer, live=live)
predictor = SupResCandle
analytics = Analytics(tracer)

trader = Trader(
    ig=ig,
    tiingo=tiingo,
    tracer=tracer,
    predictor=predictor,
    dataprocessor=dataProcessor,
    analytics=analytics,
    trainer=Trainer(analytics),
    cache=cache)

tracer.debug(f"Start trading")
trader.trade_markets(TradeType.FX)

# report
if datetime.now().hour == 18:
    tracer.debug("Create report")
    dbx = dropbox.Dropbox(env_reader.get("dropbox"))
    ds = DropBoxService(dbx, type_)
    ig.create_report(tiingo, ds)
