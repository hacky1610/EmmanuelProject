from ray import tune, air
from ray.tune import Tuner
import Tracing.ConsoleTracer
from Tracing.Tracer import Tracer
from Trainer.lstm_trainer import LSTM_Trainer
from Connectors.Loader import *
from Utils.Utils import *
import ray
from pandas import DataFrame
from Connectors.tiingo import Tiingo

class QlRayTune:

    def __init__(self, data: DataFrame, tracer: Tracer, logDirectory: str = "./logs", name: str = ""):
        self._tracer: Tracer = tracer
        self._logDirectory: str = logDirectory
        self._name: str = name
        self._data: DataFrame = data

    def _get_stop_config(self):
        return {
            "training_iteration": 25,
            # "episode_reward_mean": 0.36
        }

    def _get_tune_config(self, mode="max") -> tune.TuneConfig:
        return tune.TuneConfig(
            metric=LSTM_Trainer.METRIC,
            mode=mode
        )

    def _create_tuner(self) -> Tuner:
        param_space = {
            "df": self._data,
            "tracer": self._tracer,
            "window_size": tune.grid_search([16, 32, 64]),
            "lstm1_len": tune.grid_search([512, 256, 128, 64]),
            "lstm2_len": tune.grid_search([512, 256, 128, 64]),
            "dense_len": tune.grid_search([512, 256, 128, 64]),
            "optimizer": tune.grid_search(["Adam", "SGD"]),
        }

        return tune.Tuner(
            LSTM_Trainer,
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
        best_result = results.get_best_result(metric=LSTM_Trainer.METRIC)
        print("best hyperparameters: ", best_result.config)
        print("best hyperparameters dir: ", best_result.log_dir)
        return results, best_result.checkpoint

    def create_log_folder(self, logFolderParent: str):
        t = datetime.now().strftime("%Y%m%d_%H%M%S")
        logFolder = os.path.join(logFolderParent, f"Evaluation_{t}")
        os.mkdir(logFolder)
        return logFolder

    def evaluate(self, model_path: str):
        # TODO: Model wird zwei mal geladen
        pass


ray.init(local_mode=True, num_gpus=1)

# Prep
dp = DataProcessor()
ti = Tiingo()
df = ti.load_data_by_date("GBPUSD", "2022-08-15", "2022-12-31", dp, "1hour")

# Train
q = QlRayTune(data=df,
              tracer=Tracing.ConsoleTracer.ConsoleTracer(),
              logDirectory=Utils.Utils.get_log_dir(),
              name="LSTM")
_, checkpoint = q.train()

exit(0)

# checkpoint_path = checkpoint._local_path
# print(f"use checkpoint {checkpoint_path}")
checkpoint_path = "D:\\Code\\EmmanuelProject\\logs\\QL_Indi\\QTrainer_5982e314_5_beta1=0.9112,beta2=0.9568,decay=0.0025,epsilon=0.8233,gamma=0.9000,hiddens=64_32_16,lr=0.0023,max_cpu_fraction_2023-02-06_01-12-42\\checkpoint_000025"
# Evaluate
q = QlRayTune(stock_name="GSPC_test",
              tracer=Tracing.ConsoleTracer.ConsoleTracer(),
              logDirectory=Utils.Utils.get_log_dir(),
              name="QL_Indi")
q.evaluate(model_path=os.path.join(checkpoint_path, "model.h5"))
