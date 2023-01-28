from Connectors.IG import IG
from Data.data_processor import DataProcessor
from Tracing.LogglyTracer import LogglyTracer
from Agents.RayTune import RayTune
from Envs.igEnv import IgEnv
from Connectors.tiingo import Tiingo
import time
from datetime import date, timedelta
from Utils.Utils import read_config

#Variables
symbol = "GBPUSD"
dataProcessor = DataProcessor()
config = read_config()
tracer = LogglyTracer(config["loggly_api_key"])
tiingo = Tiingo()


while True:
    ig = IG()

    trade_df = tiingo.load_data_by_date(symbol,(date.today() - timedelta(days=2)).strftime("%Y-%m-%d"), date.today().strftime("%Y-%m-%d"), dataProcessor)
    trade_env_conf = RayTune.create_env_config(trade_df, 8, tracer)

    agTest = RayTune(tracer)
    checkpoint =  "/home/daniel/ray_results/PPO/PPO_ForexEnv_17412_00000_0_2023-01-25_00-37-40/checkpoint_000125"
    info = agTest.trade(IgEnv,trade_env_conf,checkpoint)
    time.sleep(60*30)

