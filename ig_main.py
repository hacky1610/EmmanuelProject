from Envs.forexEnv import ForexEnv
import ray
from Agents.RayTune import RayTune
from Connectors.runMetrics import RunMetric,FileHandler
from Connectors.IG import IG
from Data.data_processor import DataProcessor
import Utils.Utils
from Tracing.FileTracer import FileTracer
from pathlib import Path
import os

#Variables
symbol = "CS.D.GBPUSD.CFD.IP"
dataProcessor = DataProcessor()
tracer = FileTracer(os.path.join(Path.home(),"Emmanuel.log"))
ig = IG()

#Load Data
train_df = ig.load_data(symbol,"2022-12-01 00:00:00","2022-12-31 00:00:00",dataProcessor)
test_df = ig.load_data(symbol,"2023-01-01 00:00:00","2023-01-10 00:00:00",dataProcessor)

ray.init()

train_env_conf = RayTune.create_env_config(train_df, 8, tracer)
test_env_conf = RayTune.create_env_config(test_df, 8, tracer)

#Train
agTrain = RayTune()
results, checkpoint = agTrain.train(ForexEnv, train_env_conf)

#Test
agTest = RayTune()
info = agTest.evaluate(ForexEnv, test_env_conf,checkpoint,Utils.Utils.get_runs_dir())

rm = RunMetric(FileHandler("./runs"))
if rm.is_better_than_last(symbol,info):
    rm.save(symbol,info)
    print("This run is better than before")
else:
    print("This run is worse than before")
