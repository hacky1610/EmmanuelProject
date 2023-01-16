import datetime as dt
from matplotlib import pyplot as plt
from Tracing.FileTracer import FileTracer
from Connectors.Loader import Loader
from Agents.AgentCollection import AgentCollection
import os
from Envs.StockSignalEnv import StockSignalEnv
from ray.tune.registry import get_trainable_cls
import ray
from ray import air, tune
from ray.rllib.algorithms.ppo import PPO
ray.init()

df = Loader.loadFromOnline("USDJPY=X", dt.datetime.today() - dt.timedelta(350), dt.datetime.today())

env_conf = {
    "df":df,
    "frame_bound": (12, 100),
    "window_size": 12,
    "tracer":FileTracer("/tmp/foo.log")
}

config = (
    get_trainable_cls("PPO")
    .get_default_config()
    # or "corridor" if registered above
    .environment(StockSignalEnv, env_config=env_conf)
    .framework("tf2")


)

stop = {
    "training_iteration": 50,
    "timesteps_total": 100000,
    "episode_reward_mean": 40
}

print("Training automatically with Ray Tune")
tuner = tune.Tuner(
    "PPO",
    param_space=config.to_dict(),
    run_config=air.RunConfig(stop=stop),
)
results = tuner.fit()


