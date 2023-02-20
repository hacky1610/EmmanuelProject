import time
from Connectors.IG import IG
from Data.data_processor import DataProcessor
from Tracing.LogglyTracer import LogglyTracer
from Connectors.tiingo import Tiingo
from Logic.Utils import read_config
from Logic.trader import Trader
from Logic.trainer import Trainer

# Variables
symbol = "GBPUSD"
dataProcessor = DataProcessor()
config = read_config()
tracer = LogglyTracer(config["loggly_api_key"])
tiingo = Tiingo()
ig = IG(tracer)
train_data = Trainer.get_train_data(tiingo, symbol, dataProcessor)
trainer = Trainer({"df": train_data})
trainer.load_model("Models/model_20230217.h5")


trader = Trader(symbol, ig, tiingo, tracer, trainer, dataProcessor)

while True:
    trader.trade()
    time.sleep(60 * 60)
