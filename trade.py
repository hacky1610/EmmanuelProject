import time
from Connectors.IG import IG
from Data.data_processor import DataProcessor
from Tracing.LogglyTracer import LogglyTracer
from Connectors.tiingo import Tiingo
from Logic.Utils import read_config
from Logic.trader import Trader

# Variables
symbol = "GBPUSD"
dataProcessor = DataProcessor()
config = read_config()
tracer = LogglyTracer(config["loggly_api_key"])
tiingo = Tiingo()
ig = IG(tracer)

trader = Trader(symbol, ig, tiingo, tracer)

while True:
    trader.trade()
    time.sleep(60 * 60)
