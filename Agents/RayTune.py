from ray.tune.registry import get_trainable_cls
from ray import tune, air
from Connectors.FileOperations import FileOperations


class RayTune:

    def __init__(self, framework: str = "tf2", algorithm: str = "PPO", runsDirectory: str = "./runs"):
        self._algorithm = algorithm
        self._algoConfig = RayTune._create_algorith_config(framework, algorithm)

    def _get_stop_config(self):
        return {
            #"training_iteration": 50,
            "timesteps_total": 10000,
            #"episode_reward_mean": 1.0
        }

    def train(self, environment, env_conf: dict):
        #https://docs.ray.io/en/latest/tune/api_docs/search_space.html
        #https://medium.com/aureliantactics/ppo-hyperparameters-and-ranges-6fc2d29bccbe
        #self._algoConfig["gamma"] = tune.uniform(0.9, 0.99)
        #self._algoConfig["lr"] = tune.uniform(0.003, 5e-6)
        #self._algoConfig["clip_param"] = tune.choice([0.1, 0.2, 0.3])
        ##self._algoConfig["entropy_coeff"] = tune.uniform(0.0, 0.01)
        self._algoConfig.environment(environment, env_config=env_conf)

        tuner = tune.Tuner(
            self._algorithm,
            param_space=self._algoConfig.to_dict(),
            run_config=air.RunConfig(stop=self._get_stop_config()),
        )
        results = tuner.fit()
        # Todo: check on success
        print("best hyperparameters: ", results.get_best_result().config)
        print("best hyperparameters dir: ", results.get_best_result().log_dir)
        return True, FileOperations.get_folder_by_regex(results.get_best_result().log_dir, "checkpoint.+")

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
