from Connectors.IG import IG
from BL.data_processor import DataProcessor
from Tracing.LogglyTracer import LogglyTracer
from Connectors.tiingo import Tiingo, TradeType
from BL import Trader, Analytics, EnvReader
from Predictors import *
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
exclude = ["EURAUD"]
predictor = RsiStoch({})

trader = Trader(
    ig=ig,
    tiingo=tiingo,
    tracer=tracer,
    predictor=predictor,
    dataprocessor=dataProcessor,
    analytics=Analytics(tracer),
    trainer=Trainer())

# trade
markets = ig.get_markets(TradeType.FX)
tracer.write(f"Trade with settings {predictor.get_config_as_string()}")
for market in markets:
    symbol = market["symbol"]
    if symbol not in exclude:
        tracer.write(f"Try to trade {symbol}")
        trader.trade(market["symbol"], market["epic"], market["spread"], market["scaling"])

# report
if datetime.now().hour == 18:
    tracer.write("Create report")
    dbx = dropbox.Dropbox(env_reader.get("dropbox"))
    ds = DropBoxService(dbx, type_)
    ig.create_report(tiingo, ds)
