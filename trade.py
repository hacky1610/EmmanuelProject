import time
from Connectors.IG import IG
from Data.data_processor import DataProcessor
from Tracing.LogglyTracer import LogglyTracer
from Connectors.tiingo import Tiingo
from LSTM_Logic.Utils import read_config
from BL import Trader,Analytics
from Predictors import RSI,CCI,PredictorCollection

# Variables
symbol = "GBPUSD"
dataProcessor = DataProcessor()
config = read_config()
tracer = LogglyTracer(config["loggly_api_key"])
tiingo = Tiingo()
ig = IG(tracer)
trader = Trader(symbol=symbol,
                ig=ig,
                tiingo=tiingo,
                tracer=tracer,
                predictors=PredictorCollection([RSI({}),CCI({})]),
                dataprocessor=dataProcessor,
                analytics=Analytics(tracer))


while True:
    trader.trade()
    time.sleep(60 * 60)
