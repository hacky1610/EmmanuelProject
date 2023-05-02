from Connectors.IG import IG
from BL.data_processor import DataProcessor
from Tracing.LogglyTracer import LogglyTracer
from Connectors.tiingo import Tiingo, TradeType
from BL import Analytics, EnvReader
from BL.trader import Trader
from Predictors.rsi_bb import RsiBB
from Predictors.trainer import Trainer
from datetime import datetime
import dropbox
from Connectors.dropboxservice import DropBoxService

env_reader = EnvReader()
type_ = env_reader.get("Type")

if type_ == "DEMO":
    live = False
else:
    live = True

dataProcessor = DataProcessor()
tracer = LogglyTracer(env_reader.get("loggly_api_key"), type_)
tiingo = Tiingo(tracer=tracer, conf_reader=env_reader)
ig = IG(conf_reader=env_reader, tracer=tracer, live=live)
predictor = RsiBB
analytics = Analytics(tracer)

trader = Trader(
    ig=ig,
    tiingo=tiingo,
    tracer=tracer,
    predictor=predictor,
    dataprocessor=dataProcessor,
    analytics=analytics,
    trainer=Trainer(analytics))

tracer.debug(f"Start trading")
trader.trade_markets(TradeType.FX)
trader.trade_markets(TradeType.METAL)

# report
if datetime.now().hour == 18:
    tracer.debug("Create report")
    dbx = dropbox.Dropbox(env_reader.get("dropbox"))
    ds = DropBoxService(dbx, type_)
    ig.create_report(tiingo, ds)
