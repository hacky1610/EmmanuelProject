from Connectors.IG import IG
from Data.data_processor import DataProcessor
from Tracing.LogglyTracer import LogglyTracer
from Connectors.tiingo import Tiingo
from BL import Trader, Analytics, EnvReader
from Predictors import *

env_reader = EnvReader()
type_ = env_reader.get("Type")

if type_ == "DEMO":
    live = False
else:
    live = True

dataProcessor = DataProcessor()
tracer = LogglyTracer(env_reader.get("loggly_api_key"), type_)
tiingo = Tiingo(tracer, conf_reader=env_reader)
ig = IG(conf_reader=env_reader, tracer=tracer, live=live)

trader = Trader(
    ig=ig,
    tiingo=tiingo,
    tracer=tracer,
    predictor=CCI_EMA({}),
    dataprocessor=dataProcessor,
    analytics=Analytics(tracer))

markets = ig.get_markets()
for market in markets:
    trader.trade(market["symbol"], market["epic"], market["spread"], market["scaling"])
