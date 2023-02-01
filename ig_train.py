from Envs.forexEnv import ForexEnv
import ray
from Tuning.RayTune import RayTune
from Connectors.runMetrics import RunMetric,FileHandler
from Connectors.IG import IG
from Connectors.tiingo import Tiingo
from Data.data_processor import DataProcessor
import Utils.Utils
from Tracing.FileTracer import FileTracer
from pathlib import Path
import os
import datetime

#Variables
symbol = "GBPUSD"
dataProcessor = DataProcessor()
tracer = FileTracer(os.path.join(Path.home(),"Emmanuel.log"))
ig = IG()
tiingo = Tiingo()
logDir = Utils.Utils.get_log_dir()
window = 8
resolution = "1hour"
date = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
trainName = f"Win{window}_Res{resolution}_{date}"

#Load Data
train_df = tiingo.load_data_by_date(symbol, "2022-12-15", "2022-12-31", dataProcessor,resolution)
test_df = tiingo.load_data_by_date(symbol, "2023-01-01", "2023-01-10", dataProcessor,resolution)

ray.init(num_cpus=6)

train_env_conf = RayTune.create_env_config(train_df, window, tracer)
test_env_conf = RayTune.create_env_config(test_df, window, tracer)

#Train
agTrain = RayTune(tracer,logDirectory=logDir,name=trainName)
results, checkpoint = agTrain.train(ForexEnv, train_env_conf)

#Test
agTest = RayTune(tracer)
info = agTest.evaluate(ForexEnv, test_env_conf,checkpoint,Utils.Utils.get_runs_dir())

rm = RunMetric(FileHandler("./runs"))
if rm.is_better_than_last(symbol,info):
    rm.save(symbol,info)
    print("This run is better than before")
else:
    print("This run is worse than before")
