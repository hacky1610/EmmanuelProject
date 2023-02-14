import time

from Connectors.IG import IG
from Data.data_processor import DataProcessor
from Tracing.LogglyTracer import LogglyTracer
from Trainer.lstm_trainer import LSTM_Trainer
from Connectors.tiingo import Tiingo
from datetime import date, timedelta
from Utils.Utils import read_config

# Variables
symbol = "GBPUSD"
dataProcessor = DataProcessor()
config = read_config()
tracer = LogglyTracer(config["loggly_api_key"])
tiingo = Tiingo()

ig = IG(tracer)
train_data = tiingo.load_data_by_date(symbol, "2022-08-15", "2022-12-31", dataProcessor, "1hour")
if len(train_data) == 0:
    tracer.error("Could not load train data")
    exit(1)

trainer = LSTM_Trainer({"df": train_data})
trainer.load_model("Models/Saturn.h5")

while True:
    trade_df = tiingo.load_data_by_date(symbol, (date.today() - timedelta(days=20)).strftime("%Y-%m-%d"),
                                        None, dataProcessor)
    if len(trade_df) == 0:
        tracer.error("Could not load train data")
        break

    trade_data = trainer.filter_dataframe(trade_df)
    val, signal = trainer.trade(trade_data.values[-16:])
    if not ig.has_opened_positions():
        if signal == "buy":
            res = ig.buy("CS.D.GBPUSD.CFD.IP")
            tracer.write(f"Buy -> expected {val}")
        else:
            res = ig.sell("CS.D.GBPUSD.CFD.IP")
            tracer.write(f"Sell -> expected {val}")

        if not res:
            tracer.error("Error while open trade")

    time.sleep(60 * 60)
