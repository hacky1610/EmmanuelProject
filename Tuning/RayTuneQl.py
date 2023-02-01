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

class QlRayTune:
    _metric:str = "total_profit"

    def __init__(self, stock_name:str, tracer: Tracer, logDirectory: str = "./logs",name:str=""):
        self._tracer: Tracer = tracer
        self._logDirectory:str = logDirectory
        self._name:str = name
        self._stock_name:str = stock_name

    def _get_stop_config(self):
        return {
            "training_iteration": 5,
            # "episode_reward_mean": 0.36
        }

    def _get_tune_config(self, mode="max"):
        return tune.TuneConfig(
            metric=self._metric,
            mode=mode,
        )

    def _create_tuner(self) -> Tuner:
        param_space = {
            "scaling_config": ScalingConfig(use_gpu=True),
            "stock_name": self._stock_name,
            "tracer": self._tracer
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

    def evaluate(self, model_name:str):
        model = load_model("models/" + model_name)
        window_size = model.layers[0].input.shape.as_list()[1]

        agent = QlAgent(window_size, True, model_name)
        data = getStockDataVec(self.stock_name)
        l = len(data) - 1

        state = getState(data, 0, window_size + 1)
        total_profit = 0
        agent.inventory = []

        for t in range(l):
            action = agent.act(state)

            # sit
            next_state = getState(data, t + 1, window_size + 1)
            reward = 0

            if action == 1:  # buy
                agent.inventory.append(data[t])
                print("Buy: " + formatPrice(data[t]))

            elif action == 2 and len(agent.inventory) > 0:  # sell
                bought_price = agent.inventory.pop(0)
                reward = max(data[t] - bought_price, 0)
                total_profit += data[t] - bought_price
                print("Sell: " + formatPrice(data[t]) + " | Profit: " + formatPrice(data[t] - bought_price))

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

ray.init(local_mode=True)

#Train
q = QlRayTune(stock_name="GSPC",
              tracer=Tracing.ConsoleTracer.ConsoleTracer(),
              logDirectory=Utils.Utils.get_log_dir(),
              name="QL")
q.train()

#Evaluate
q = QlRayTune(stock_name="GSPC_test",
              tracer=Tracing.ConsoleTracer.ConsoleTracer(),
              logDirectory=Utils.Utils.get_log_dir(),
              name="QL")
q.evaluate()
