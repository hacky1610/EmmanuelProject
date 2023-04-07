from Connectors.IG import IG
from Data.data_processor import DataProcessor
from Tracing.LogglyTracer import LogglyTracer
from Connectors.tiingo import Tiingo
from BL import Trader, Analytics, EnvReader
from Predictors import *

dataProcessor = DataProcessor()
tracer = LogglyTracer(EnvReader().get("loggly_api_key"))
tiingo = Tiingo(tracer,conf_reader=EnvReader())
ig = IG(tracer,conf_reader=EnvReader())

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

