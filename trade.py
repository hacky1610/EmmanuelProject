import time
from Connectors.IG import IG
from Data.data_processor import DataProcessor
from Tracing.LogglyTracer import LogglyTracer
from Connectors.tiingo import Tiingo
from LSTM_Logic.Utils import read_config
from BL import Trader,Analytics
from Predictors import *

# Variables
dataProcessor = DataProcessor()
config = read_config()
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

stock_list = ["EURUSD","GBPUSD"]

while True:
    for stock in stock_list:
        trader.trade(stock)

    time.sleep(60 * 60)
