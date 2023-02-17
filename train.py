import os
import ray
from Data.data_processor import DataProcessor
from Connectors.tiingo import Tiingo
from Logic.tuner import Tuner
from Tracing.ConsoleTracer import ConsoleTracer
from Logic import Utils

ray.init(local_mode=True, num_gpus=1,num_cpus=os.cpu_count()-2)

# Prep
dp = DataProcessor()
ti = Tiingo()
df = ti.load_data_by_date("GBPUSD", "2022-08-15", "2022-12-31", dp, "1hour")

# Train
q = Tuner(data=df,
          tracer=ConsoleTracer(),
          logDirectory=Utils.get_log_dir(),
          name="Saturn")
_, checkpoint = q.train()

