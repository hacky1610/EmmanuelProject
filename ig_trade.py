from Connectors.IG import IG
from Data.data_processor import DataProcessor
from Tracing.LogglyTracer import LogglyTracer
from Tuning.RayTuneQl import QlRayTune
from Trainer.lstm_trainer import LSTM_Trainer
from Connectors.tiingo import Tiingo
from datetime import date, timedelta
from Utils.Utils import read_config

#Variables
symbol = "GBPUSD"
dataProcessor = DataProcessor()
config = read_config()
tracer = LogglyTracer(config["loggly_api_key"])
tiingo = Tiingo()


ig = IG()
trainData = QlRayTune.get_training_data(tiingo)
trade_df = tiingo.load_data_by_date(symbol,(date.today() - timedelta(days=2)).strftime("%Y-%m-%d"), date.today().strftime("%Y-%m-%d"), dataProcessor)


trainer = LSTM_Trainer({"df":trainData})

val, signal = trainer.trade(trade_df.filter("close").values)
print(signal)





