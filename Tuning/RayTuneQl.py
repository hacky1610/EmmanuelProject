from ray import tune, air
from ray.tune import Tuner
import Tracing.ConsoleTracer
import Utils.Utils
from Tracing.Tracer import Tracer
from Trainer.q_trainer import QTrainer
from Connectors.Loader import *
from ray.air.config import ScalingConfig
from keras.models import load_model
from Utils.Utils import *
from Agents.QlAgent import QlAgent
import ray
from ray.tune.search.bayesopt import BayesOptSearch

class QlRayTune:
    _metric:str = "total_profit"

    def __init__(self, stock_name:str, tracer: Tracer, logDirectory: str = "./logs",name:str=""):
        self._tracer: Tracer = tracer
        self._logDirectory:str = logDirectory
        self._name:str = name
        self._stock_name:str = stock_name

    def _get_stop_config(self):
        return {
            "training_iteration": 25,
            # "episode_reward_mean": 0.36
        }

    def _get_tune_config(self, mode="max"):
        bayesopt = BayesOptSearch(metric=self._metric, mode="max")

        return tune.TuneConfig(
            search_alg=bayesopt ,
            num_samples=60
        )

    def _create_tuner(self) -> Tuner:
        param_space = {
            "scaling_config": ScalingConfig(use_gpu=True),
            "stock_name": self._stock_name,
            "tracer": self._tracer,
            "gamma": 0.90, #tune.grid_search([0.90,0.95]),
            "lr": tune.uniform(0.0001, 0.005), #tune.grid_search([0.00008, 0.0001]),
            "hiddens": [64,32,16],
            "beta1": tune.uniform(0.85, 0.95),
            "beta2": tune.uniform(0.95, 0.999),
            "epsilon":  tune.uniform(0.75, 0.95),
            "decay": tune.uniform(0.001, 0.006),
        }


        return tune.Tuner(
            QTrainer,
            param_space=param_space,
            run_config=air.RunConfig(stop=self._get_stop_config(),
                                     log_to_file=True,
                                     local_dir=self._logDirectory,
                                     name=self._name,
                                     checkpoint_config=air.CheckpointConfig(checkpoint_frequency=2)),
            tune_config=self._get_tune_config(),
        )

    def train(self):
        tuner = self._create_tuner()
        results = tuner.fit()
        # Todo: check on success
        best_result = results.get_best_result(metric=self._metric)
        print("best hyperparameters: ", best_result.config)
        print("best hyperparameters dir: ", best_result.log_dir)
        return results, best_result.checkpoint

    def create_log_folder(self, logFolderParent: str):
        t = datetime.now().strftime("%Y%m%d_%H%M%S")
        logFolder = os.path.join(logFolderParent, f"Evaluation_{t}")
        os.mkdir(logFolder)
        return logFolder

    def evaluate(self, model_path:str):
        #TODO: Model wird zwei mal geladen
        model = load_model(model_path)
        window_size = model.layers[0].input.shape.as_list()[1]

        agent = QlAgent(shape=(1,10), is_eval=True, model_path=model_path)
        data = getStockDataVec(self._stock_name)
        l = len(data) - 1

        state = getState(data, 0, window_size + 1)
        total_profit = 0
        agent.inventory = []



        for t in range(l):
            action = agent.act(state)
            # sit
            next_state = getState(data, t + 1, window_size + 1)
            reward = 0

            current_price = data[t]

            for i in range(t, len(data)):
                futurePrice = data[i]
                if (action == 0):  # Buy
                    if futurePrice > current_price + 10:
                        reward = futurePrice - current_price
                        break
                    elif futurePrice < current_price - 10:
                        reward = futurePrice - current_price
                        break
                elif action == 1:  # Sell
                    if futurePrice < current_price - 10:
                        reward = current_price - futurePrice
                        break
                    elif futurePrice > current_price + 10:
                        reward = current_price - futurePrice
                        break

            total_profit += reward

            done = True if t == l - 1 else False
            agent.memory.append((state, action, reward, next_state, done))
            state = next_state

            if done:
                print("--------------------------------")
                print(self._stock_name + " Total Profit: " + formatPrice(total_profit))
                print("--------------------------------")

    def trade(self, environment, env_conf: dict, checkpointFolder: str):
        self._algoConfig.environment(environment, env_config=env_conf)
        algorithm = self._algoConfig.build()
        algorithm.restore(checkpointFolder)

        env = environment(env_conf)
        obs = env.reset()
        a = algorithm.compute_single_action(obs)
        env.trade(a)

ray.init(local_mode=True,num_gpus=1 )

#Train
q = QlRayTune(stock_name="GSPC",
              tracer=Tracing.ConsoleTracer.ConsoleTracer(),
              logDirectory=Utils.Utils.get_log_dir(),
              name="QL_Indi")
#_, checkpoint = q.train()

#checkpoint_path = checkpoint._local_path
#print(f"use checkpoint {checkpoint_path}")
checkpoint_path = "D:\\Code\\EmmanuelProject\\logs\\QL_Indi\\QTrainer_5982e314_5_beta1=0.9112,beta2=0.9568,decay=0.0025,epsilon=0.8233,gamma=0.9000,hiddens=64_32_16,lr=0.0023,max_cpu_fraction_2023-02-06_01-12-42\\checkpoint_000025"
#Evaluate
q = QlRayTune(stock_name="GSPC_test",
              tracer=Tracing.ConsoleTracer.ConsoleTracer(),
              logDirectory=Utils.Utils.get_log_dir(),
              name="QL_Indi")
q.evaluate(model_path=os.path.join(checkpoint_path,"model.h5"))
