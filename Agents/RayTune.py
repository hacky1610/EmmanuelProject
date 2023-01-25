from ray.tune.registry import get_trainable_cls
from ray import tune, air
from ray.tune import Tuner
from ray.tune import ResultGrid
from Connectors.FileOperations import FileOperations
from ray.tune.search.bayesopt import BayesOptSearch
import os
from datetime import datetime

class RayTune:

    _metric = "episode_reward_mean"

    def __init__(self, framework: str = "tf2", algorithm: str = "PPO", runsDirectory: str = "./runs"):
        self._algorithm = algorithm
        self._algoConfig = RayTune._create_algorith_config(framework, algorithm)

    def _get_stop_config(self):
        return {
            #"training_iteration": 50,
            "timesteps_total": 500000,
            #"episode_reward_mean": 0.36
        }

    def _get_tune_config(self,mode="max"):
        return tune.TuneConfig(
            metric=self._metric,
            mode=mode,
        )

    def _create_tuner(self, environment, env_conf: dict) -> Tuner:
        # https://docs.ray.io/en/latest/tune/api_docs/search_space.html
        # https://medium.com/aureliantactics/ppo-hyperparameters-and-ranges-6fc2d29bccbe
        self._algoConfig["gamma"] = 0.9
        self._algoConfig["lr"] = 0.0001
        self._algoConfig["clip_param"] = 0.1
        self._algoConfig["sgd_minibatch_size"] = 128
        self._algoConfig["num_sgd_iter"] = 30
        self._algoConfig["kl_target"] = 0.003
        self._algoConfig["kl_coeff"] = 0.003
        self._algoConfig["entropy_coeff"] = 0.0

        self._algoConfig.environment(environment, env_config=env_conf)

        return tune.Tuner(
            self._algorithm,
            param_space=self._algoConfig.to_dict(),
            run_config=air.RunConfig(stop=self._get_stop_config(), log_to_file=True),
            tune_config=self._get_tune_config(),

        )

    def train(self, environment, env_conf: dict):

        tuner = self._create_tuner(environment,env_conf)
        results = tuner.fit()
        # Todo: check on success
        best_result = results.get_best_result(metric=self._metric)
        print("best hyperparameters: ", best_result.config)
        print("best hyperparameters dir: ", best_result.log_dir)
        return results, best_result.checkpoint

    def create_log_folder(self,logFolderParent:str):
        t = datetime.now().strftime("%Y%m%d_%H%M%S")
        logFolder = os.path.join(logFolderParent, f"Evaluation_{t}")
        os.mkdir(logFolder)
        return logFolder
    def evaluate(self, environment, env_conf: dict, checkpointFolder: str,logFolderParent:str):
        logFolder = self.create_log_folder(logFolderParent)

        self._algoConfig.environment(environment, env_config=env_conf)
        algorithm = self._algoConfig.build()
        algorithm.restore(checkpointFolder)

        env = environment(env_conf)
        obs = env.reset()
        info = None

        while True:
            a = algorithm.compute_single_action(obs)
            obs, step_reward, _done, info = env.step(a)
            if _done:
                break

        env.plot(os.path.join(logFolder))
        env.save_report(logFolder)
        print(info)
        return info

    def trade(self,environment, env_conf: dict, checkpointFolder: str):
        self._algoConfig.environment(environment, env_config=env_conf)
        algorithm = self._algoConfig.build()
        algorithm.restore(checkpointFolder)

        env = environment(env_conf)
        obs = env.reset()
        a = algorithm.compute_single_action(obs)
        env.trade(a)


    @staticmethod
    def _create_algorith_config(framework: str = "tf2", algo: str = "PPO"):
        config = (
            get_trainable_cls(algo)
            .get_default_config()
            .framework(framework)
        )
        return config

    @staticmethod
    def create_env_config(dataframe, window_size, tracer):
        config = {
            "df": dataframe,
            "window_size": window_size,
            "tracer": tracer
        }
        return config
