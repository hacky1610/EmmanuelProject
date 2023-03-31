import os
import ray
from Data.data_processor import DataProcessor
from Connectors.tiingo import Tiingo
from Predictors.rsi import RSI
from BL.tuner import Tuner
from Tracing.ConsoleTracer import ConsoleTracer

ray.init(local_mode=True)

# Prep
dp = DataProcessor()
ti = Tiingo()
df = ti.load_data_by_date("GBPUSD","2023-01-02","2023-02-28",dp)
tuner = Tuner(df,ConsoleTracer(),RSI)
tuner.train()
print("")

