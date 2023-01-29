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

    trade_df = tiingo.load_data_by_date(symbol,(date.today() - timedelta(days=2)).strftime("%Y-%m-%d"), date.today().strftime("%Y-%m-%d"), dataProcessor,resolution="15min")
    trade_env_conf = RayTune.create_env_config(trade_df, 8, tracer)

    agTest = RayTune(tracer)
    checkpoint =  "Models/PPO_Win8_2501"
    info = agTest.trade(IgEnv,trade_env_conf,checkpoint)
    time.sleep(60*60)


