from Envs.forexEnv import ForexEnv
import ray
from Agents.RayTune import RayTune
from Connectors.runMetrics import RunMetric,FileHandler
from Connectors.IG import IG
from Connectors.tiingo import Tiingo
from Data.data_processor import DataProcessor
import Utils.Utils
from Tracing.FileTracer import FileTracer
from pathlib import Path
import os

#Variables
symbol = "GBPUSD"
dataProcessor = DataProcessor()
tracer = FileTracer(os.path.join(Path.home(),"Emmanuel.log"))
tiingo = Tiingo()

#Load Data
test_df = tiingo.load_data_by_date(symbol, "2023-01-01", "2023-01-10", dataProcessor,"4hour")
test_env_conf = RayTune.create_env_config(test_df, 12, tracer,0.0009,0.0009)

checkpoint = os.path.join(Utils.Utils.get_project_dir(),"Models/PPO_Win12_4hour_L9_S9_2801")
#Test
agTest = RayTune(tracer)
info = agTest.evaluate(ForexEnv, test_env_conf,checkpoint,Utils.Utils.get_runs_dir())

rm = RunMetric(FileHandler("./runs"))
if rm.is_better_than_last(symbol,info):
    rm.save(symbol,info)
    print("This run is better than before")
else:
    print("This run is worse than before")
