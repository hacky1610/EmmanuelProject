import time
from Connectors.IG import IG
from BL.data_processor import DataProcessor
from Tracing.LogglyTracer import LogglyTracer
from Connectors.tiingo import Tiingo
from BL import Trader, Analytics, ConfigReader
from Predictors import *

live_trade = False

dataProcessor = DataProcessor()
conf_reader = ConfigReader(live_config=live_trade)
tracer = LogglyTracer(conf_reader.get("loggly_api_key"),"DEMO")
tiingo = Tiingo(tracer=tracer,conf_reader=conf_reader)
ig = IG(tracer=tracer,conf_reader=conf_reader,live=live_trade)

trader = Trader(
    ig=ig,
    tiingo=tiingo,
    tracer=tracer,
    predictor=RSI_STOCK_MACD({}),
    dataprocessor=dataProcessor,
    analytics=Analytics(tracer))

while True:
    markets = ig.get_markets()
    for market in markets:
        trader.trade(market["symbol"], market["epic"], market["spread"], market["scaling"])

    time.sleep(60 * 60)
