from Connectors.IG import IG
from BL.data_processor import DataProcessor
from Tracing.LogglyTracer import LogglyTracer
from Connectors.tiingo import Tiingo, TradeType
from BL import Analytics, ConfigReader
from BL.trader import Trader
from Predictors.rsi_bb import RsiBB
from Predictors.trainer import Trainer


live_trade = False

dataProcessor = DataProcessor()
conf_reader = ConfigReader(live_config=live_trade)
tracer = LogglyTracer(conf_reader.get("loggly_api_key"),"DEMO")
tiingo = Tiingo(tracer=tracer,conf_reader=conf_reader)
ig = IG(tracer=tracer,conf_reader=conf_reader,live=live_trade)
analytics = Analytics(tracer)
predictor = RsiBB({})

trader = Trader(
    ig=ig,
    tiingo=tiingo,
    tracer=tracer,
    predictor=predictor,
    dataprocessor=dataProcessor,
    analytics=analytics,
    trainer=Trainer(analytics)
    )

markets = ig.get_markets(TradeType.FX)
for market in markets:
    trader.trade(
        symbol=market["symbol"],
        epic=market["epic"],
        spread=market["spread"],
        scaling=market["scaling"],
        trade_type=TradeType.FX,
        size=market["size"],
        currency=market["currency"])



