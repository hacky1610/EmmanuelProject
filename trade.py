import time
from Connectors.IG import IG
from Data.data_processor import DataProcessor
from Tracing.LogglyTracer import LogglyTracer
from Connectors.tiingo import Tiingo
from BL import Trader, Analytics, ConfigReader
from Predictors import *

dataProcessor = DataProcessor()
config = ConfigReader().read_config()
tracer = LogglyTracer(config["loggly_api_key"])
tiingo = Tiingo()
ig = IG(tracer)

trader = Trader(
    ig=ig,
    tiingo=tiingo,
    tracer=tracer,
    predictor=CCI_EMA({}),
    dataprocessor=dataProcessor,
    analytics=Analytics(tracer))

while True:
    markets = ig.get_markets()
    for market in markets:
        trader.trade(market["symbol"], market["epic"], market["spread"], market["scaling"])

    time.sleep(60 * 60)
