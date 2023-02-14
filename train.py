import os
import ray
from Data.data_processor import DataProcessor
from Connectors.tiingo import Tiingo
from Tuning.RayTuneQl import QlRayTune
import Utils
from Tracing.ConsoleTracer import ConsoleTracer

ray.init(local_mode=True, num_gpus=1,num_cpus=os.cpu_count()-2)

# Prep
dp = DataProcessor()
ti = Tiingo()
df = ti.load_data_by_date("GBPUSD", "2022-08-15", "2022-12-31", dp, "1hour")

# Train
q = QlRayTune(data=df,
              tracer=ConsoleTracer(),
              logDirectory=Utils.Utils.get_log_dir(),
              name="Saturn")
_, checkpoint = q.train()

