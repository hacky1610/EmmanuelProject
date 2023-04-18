import time
from Connectors.IG import IG
from BL.data_processor import DataProcessor
from Tracing.LogglyTracer import LogglyTracer
from Connectors.tiingo import Tiingo,TradeType
from BL import Trader, Analytics, ConfigReader
from Predictors.rsi_stoch import RsiStoch
from Predictors.trainer import Trainer

live_trade = False

dataProcessor = DataProcessor()
conf_reader = ConfigReader(live_config=live_trade)
tracer = LogglyTracer(conf_reader.get("loggly_api_key"),"DEMO")
tiingo = Tiingo(tracer=tracer,conf_reader=conf_reader)
ig = IG(tracer=tracer,conf_reader=conf_reader,live=live_trade)
analytics = Analytics(tracer)

trader = Trader(
    ig=ig,
    tiingo=tiingo,
    tracer=tracer,
    predictor=RsiStoch({}),
    dataprocessor=dataProcessor,
    analytics=analytics,
    trainer=Trainer(analytics)
    )

while True:
    for market in ig.get_markets(TradeType.FX):
        trader.trade(market["symbol"], market["epic"], market["spread"], market["scaling"])

    #for market in ig.get_markets(TradeType.CRYPTO):
    #    if market["epic"] == "CS.D.BITCOIN.CFD.IP":
    #        trader.trade("btcusd", market["epic"], market["spread"], market["scaling"],100,TradeType.CRYPTO,0.01)





    time.sleep(60 * 60)
