from ray import tune, air
from ray.tune import Tuner
from Tracing.Tracer import Tracer
from Trainer.lstm_trainer import LSTM_Trainer
from Connectors.Loader import *
from Utils.Utils import *
from pandas import DataFrame
from Models import *

class QlRayTune:

    def __init__(self, data: DataFrame, tracer: Tracer, logDirectory: str = "./logs", name: str = ""):
        self._tracer: Tracer = tracer
        self._logDirectory: str = logDirectory
        self._name: str = name
        self._data: DataFrame = data

    def _get_stop_config(self):
        return {
            "training_iteration": 10,
            # "episode_reward_mean": 0.36
        }

    def _get_tune_config(self, mode="max") -> tune.TuneConfig:
        return tune.TuneConfig(
            metric=LSTM_Trainer.METRIC,
            mode=mode,
            num_samples=40
        )

    def _create_tuner(self) -> Tuner:
        model_type = Saturn

        param_space = {
            "df": self._data,
            "tracer": self._tracer,
            "model_type": model_type,
            "optimizer": "Adam"
        }
        param_space.update(model_type.get_tuner())

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



