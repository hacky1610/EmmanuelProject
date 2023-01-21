from ray.tune.registry import get_trainable_cls
from ray import tune, air
from ray.tune import ResultGrid
from Connectors.FileOperations import FileOperations
from ray.tune.search.bayesopt import BayesOptSearch

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

    def train(self, environment, env_conf: dict):
        #https://docs.ray.io/en/latest/tune/api_docs/search_space.html
        #https://medium.com/aureliantactics/ppo-hyperparameters-and-ranges-6fc2d29bccbe
        self._algoConfig["gamma"] = 0.9
        self._algoConfig["lr"] = 0.0001
        self._algoConfig["clip_param"] = 0.1
        self._algoConfig["sgd_minibatch_size"] = 128
        self._algoConfig["num_sgd_iter"] = 30

        ##self._algoConfig["entropy_coeff"] = tune.uniform(0.0, 0.01)
        #env_conf["windows_size"] = tune.choice([8, 16, 32, 64])

        self._algoConfig.environment(environment, env_config=env_conf)

        tuner = tune.Tuner(
            self._algorithm,
            param_space=self._algoConfig.to_dict(),
            run_config=air.RunConfig(stop=self._get_stop_config(),log_to_file=True),
            tune_config=self._get_tune_config(),

        )
        results = tuner.fit()
        # Todo: check on success
        best_result = results.get_best_result(metric=self._metric)
        print("best hyperparameters: ", best_result.config)
        print("best hyperparameters dir: ", best_result.log_dir)
        return results, best_result.checkpoint

    def evaluate(self, environment, env_conf: dict, checkpointFolder: str):
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

        env.plot()
        print(info)
        return info

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
