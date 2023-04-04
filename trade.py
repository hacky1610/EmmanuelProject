import time
from Connectors.IG import IG
from Data.data_processor import DataProcessor
from Tracing.LogglyTracer import LogglyTracer
from Connectors.tiingo import Tiingo
from LSTM_Logic.Utils import read_config
from BL import Trader, Analytics
from Predictors import *
import pandas as pd

# Variables
stock_list = pd.read_csv("./Data/ForexList.csv")
stock_list.set_index(stock_list.currency_pair_code, inplace=True)

dataProcessor = DataProcessor()
config = read_config()
tracer = LogglyTracer(config["loggly_api_key"])
tiingo = Tiingo()
ig = IG(tracer, stock_list)

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
        trader.trade(market["symbol"],market["epic"],market["spread"])

    time.sleep(60 * 60)
