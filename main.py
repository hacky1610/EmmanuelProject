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

ray.init()
symbol = "GBPUSD=X"
tracer = FileTracer(os.path.join(Path.home(),"Emmanuel.log"))
dataProcessor = DataProcessor()
train_df = Loader.loadFromOnline(symbol,datetime(2021, 6, 11), datetime(2022, 11, 15),dataProcessor)
test_df = Loader.loadFromOnline(symbol, datetime(2022, 10, 3), datetime(2023, 12, 20),dataProcessor)

train_env_conf = RayTune.create_env_config(train_df, 8, tracer)
test_env_conf = RayTune.create_env_config(test_df, 8, tracer)

agTrain = RayTune()
results, checkpoint = agTrain.train(ForexEnv, train_env_conf)

agTest = RayTune()
#checkpoint =  "/home/daniel/ray_results/PPO/PPO_StockSignalEnv_54042863_1_disable_action_flattening=False,disable_execution_plan_api=True,disable_preprocessor_api=False,fake__2023-01-19_13-17-46"
info = agTest.evaluate(ForexEnv, test_env_conf,checkpoint)
#info = agTest.evaluate(ForexEnv, train_env_conf,checkpoint)

rm = RunMetric(FileHandler("./runs"))

results.get_dataframe().to_csv("./runs/resultgrid.csv")
if rm.is_better_than_last(symbol,info):
    rm.save(symbol,info)
    print("This run is better than before")
else:
    print("This run is worse than before")

