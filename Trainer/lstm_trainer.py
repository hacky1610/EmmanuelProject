from ray.tune import Trainable
import os
import math
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from Models import Saturn, BaseModel
from pandas import DataFrame


class LSTM_Trainer(Trainable):
    METRIC = "signal_accuracy"
    _min_rsme: float
    _model_type: BaseModel
    _model: BaseModel
    _config: dict
    _max_signal_accuracy: float
    _all_data_df: DataFrame
    _all_data: np.array
    _train_data_len: int
    _scaler: MinMaxScaler
    _all_data_scaled: np.array
    _window_size: int
    _batch_size: int
    _epoch_count: int
    _name: str
    _model_path: str
    _num_features = 1

    def setup(self, config):
        df = config.get("df")
        self._model_type = config.get("model_type", Saturn)
        self._config = config
        self._max_signal_accuracy = 0.0
        self._min_rsme = 100.0
        self._all_data_df = df.filter(["close"])
        self._all_data = self._all_data_df.values
        self._train_data_len = math.ceil(len(self._all_data) * 0.8)

        self._scaler = MinMaxScaler(feature_range=(0, 1))
        self._all_data_scaled = self._scaler.fit_transform(self._all_data)
        self._window_size: int = config.get("window_size", 16)
        self._optimizer = config.get("optimizer ", "Adam")

        self._name = config.get("name ", "default")
        self._model = self._model_type(self._config)
        self._model.compile(optimizer=self._optimizer)
        self._model_path = f"{self._name}.h5"
        self._epoch_count = config.get("epoch_count", 5)
        self._batch_size = config.get("batch_size", 32)

    def step(self):
        train_data = self._all_data_scaled[0:self._train_data_len, :]

        x_train = []
        y_train = []

        for i in range(self._window_size, len(train_data)):
            x_train.append(train_data[i - self._window_size:i, 0])
            y_train.append(train_data[i, 0])

        x_train, y_train = np.array(x_train), np.array(y_train)
        x_train = self._model.reshape(x_train)

        self._model.fit(x_train, y_train, batch_size=self._batch_size, epochs=self._epoch_count)

        accuracy = self.calc_accuracy(self._all_data_df)
        if accuracy > self._max_signal_accuracy:
            self._model.save(os.path.join(self.logdir, f"model_{self._iteration}.h5"))
            self._max_signal_accuracy = accuracy

        current_rmse = self.calc_rmse()
        if current_rmse < self._min_rsme:
            self._min_rsme = current_rmse

        return {"done": False, self.METRIC: accuracy,
                "rmse": current_rmse,
                "max_signal_accuracy": self._max_signal_accuracy,
                "min_rsme": self._min_rsme}

    def save_model(self):
        self._model.save(self._model_path)

    def load_model(self):
        self._model = self._model_type({})
        self._model.load(self._model_path)

    def trade(self, data):

        last_scaled = self._scaler.transform(data)
        x_test = [last_scaled]
        x_test = np.array(x_test)
        x_test = self._model.reshape(x_test)
        prediction = self._model.predict(x_test)
        now = x_test[0][-1][0]
        future_scaled = prediction[0][0]
        signal = LSTM_Trainer.get_signal(now, future_scaled)

        prediction = self._scaler.inverse_transform(prediction)
        return prediction[0][0], signal

    def calc_rmse(self):
        test_data = self._all_data_scaled[self._train_data_len - self._window_size:, :]
        x_test = []
        y_test = self._all_data[self._train_data_len:, :]
        for i in range(self._window_size, len(test_data)):
            x_test.append(test_data[i - self._window_size:i, 0])

        x_test = np.array(x_test)
        x_test = self._model.reshape(x_test)
        predictions = self._model.predict(x_test)
        predictions = self._scaler.inverse_transform(predictions)
        return np.sqrt(np.mean(predictions - y_test) ** 2)

    def calc_accuracy(self, close_prices):
        correct_signals = 0
        incorrect_signals = 0

        for i in range(1, 30):
            last_prices = close_prices[-self._window_size - i:-i].values
            future = close_prices.to_numpy()[-i][0]
            now = close_prices.to_numpy()[-i - 1][0]

            prediction, signal = self.trade(last_prices)
            correct_signal = LSTM_Trainer.get_signal(now, future)

            if correct_signal == signal:
                correct_signals += 1
            else:
                incorrect_signals += 1

        return 100 * correct_signals / (correct_signals + incorrect_signals)

    @staticmethod
    def get_signal(now: float, future: float) -> str:
        if future > now:
            return "buy"
        else:
            return "sell"

    def save_checkpoint(self, chkpt_dir):
        return chkpt_dir

    def load_checkpoint(self, item):
        self.iter = item["iter"]


    def reset_config(self, new_config):
        self._tracer.write("reset_config called")
        if "fake_reset_not_supported" in self.config:
            return False
        self.num_resets += 1
        return True
