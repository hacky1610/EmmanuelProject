from Connectors.IG import IG
from Data.data_processor import DataProcessor
from Tracing.FileTracer import FileTracer
from pathlib import Path
from Agents.RayTune import RayTune
from Envs.igEnv import IgEnv
import os

#Variables
symbol = "CS.D.GBPUSD.CFD.IP"
dataProcessor = DataProcessor()
tracer = FileTracer(os.path.join(Path.home(),"Emmanuel.log"))
ig = IG()

trade_df = ig.load_data_by_range(symbol,40 , dataProcessor)
trade_env_conf = RayTune.create_env_config(trade_df, 24, tracer)

agTest = RayTune()
checkpoint =  "/home/daniel/ray_results/PPO/PPO_StockSignalEnv_54042863_1_disable_action_flattening=False,disable_execution_plan_api=True,disable_preprocessor_api=False,fake__2023-01-19_13-17-46"
info = agTest.trade(IgEnv,trade_env_conf,checkpoint)


