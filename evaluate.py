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
test_df = tiingo.load_data_by_date(symbol, "2023-01-01", "2023-01-10", dataProcessor,"1hour")
test_env_conf = RayTune.create_env_config(test_df, 8, tracer)

checkpoint = os.path.join(Utils.Utils.get_project_dir(),"logs/Win8_Res1hour_20230129_232309/PPO_ForexEnv_872d6_00000_0_2023-01-29_23-23-17/checkpoint_000125")
#Test
agTest = RayTune(tracer,algorithm="PPO")
info = agTest.evaluate(ForexEnv, test_env_conf,checkpoint,Utils.Utils.get_runs_dir())

rm = RunMetric(FileHandler("./runs"))
if rm.is_better_than_last(symbol,info):
    rm.save(symbol,info)
    print("This run is better than before")
else:
    print("This run is worse than before")