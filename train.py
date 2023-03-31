import os
#import ray
from Data.data_processor import DataProcessor
from Connectors.tiingo import Tiingo
from Predictors.rsi import RSI

#ray.init(local_mode=True, num_gpus=1, num_cpus=os.cpu_count() - 2)

# Prep
dp = DataProcessor()
ti = Tiingo()
df = ti.load_data_by_date("GBPUSD","2023-01-02","2023-02-28",dp)
rsi = RSI({})
reward, success = rsi.evaluate(df)
print("")

