import Utils.Utils
from Tracing.FileTracer import FileTracer
from Connectors.Loader import Loader
from Envs.forexEnv import ForexEnv
import ray
from ray import tune
from datetime import datetime
from Agents.RayTune import RayTune
from Connectors.runMetrics import RunMetric,FileHandler
from pathlib import Path
import os
from Data.data_processor import DataProcessor

symbol = "GBPUSD=X"
tracer = FileTracer(os.path.join(Path.home(),"Emmanuel.log"))
dataProcessor = DataProcessor()
test_df = Loader.loadFromOnline(symbol, datetime(2022, 10, 3), datetime(2023, 12, 20),dataProcessor)
test_env_conf = RayTune.create_env_config(test_df, 8, tracer)

agTest = RayTune()
checkpoint =  "/home/daniel/ray_results/PPO/PPO_ForexEnv_12b12_00000_0_2023-01-23_11-02-41/checkpoint_000125"
info = agTest.evaluate(ForexEnv, test_env_conf,checkpoint,Utils.Utils.get_runs_dir())

rm = RunMetric(FileHandler("./runs"))

if rm.is_better_than_last(symbol,info):
    rm.save(symbol,info)
    print("This run is better than before")
else:
    print("This run is worse than before")

