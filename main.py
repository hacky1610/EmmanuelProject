from Tracing.FileTracer import FileTracer
from Connectors.Loader import Loader
from Envs.StockSignalEnv import StockSignalEnv
import ray
from datetime import datetime
from Agents.RayTune import RayTune
from pathlib import Path
import os
from matplotlib import pyplot as plt

ray.init()
tracer = FileTracer(os.path.join(Path.home(),"Emmanuel.log"))
train_df = Loader.loadFromOnline("GBPUSD=X", datetime(2022, 6, 11), datetime(2022, 11, 15))
test_df = Loader.loadFromOnline("GBPUSD=X", datetime(2022, 11, 3), datetime(2023, 12, 20))

train_env_conf = RayTune.create_env_config(train_df, (12, len(train_df)), 12, tracer)
test_env_conf = RayTune.create_env_config(test_df, (12, len(test_df)), 12, tracer)

agTrain = RayTune()
result, checkpoint = agTrain.train(StockSignalEnv, train_env_conf)

if result:
    agTest = RayTune()
    #checkpoint =  "/home/daniel/ray_results/PPO/PPO_StockSignalEnv_ce7a9_00000_0_2023-01-17_11-36-31/checkpoint_000026"
    agTest.evaluate(StockSignalEnv, test_env_conf,checkpoint)
