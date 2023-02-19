from ray.tune import Trainable
import os
import math
import numpy as np
from Data.scaler import Scaler
from Models import Saturn, BaseModel
from pandas import DataFrame
from Connectors.tiingo import Tiingo
from Data.data_processor import DataProcessor


class Trainer(Trainable):
    METRIC = "signal_accuracy"
    _min_rsme: float
    _model_type: BaseModel
    _model: BaseModel
    _config: dict
    _max_signal_accuracy: float
    _train_data_len: int
    _scaler: Scaler
    _window_size: int
    _batch_size: int
    _epoch_count: int
    _name: str
    _model_path: str
    _num_features = 1
    _all_close_prices_df: DataFrame
    _all_features_df: DataFrame
    _all_close_prices: np.array
    _all_features: np.array
    _all_features_scaled: np.ndarray
    _all_close_prices_scaled: np.ndarray

    def setup(self, config):
        df = config.get("df")
        self._model_type = config.get("model_type", Saturn)
        self._config = config

        self._max_signal_accuracy = 0.0
        self._min_rsme = 100.0

        self._all_close_prices_df = df.filter(["close"])
        self._all_features_df = self.filter_dataframe(df)
        self._all_close_prices = self._all_close_prices_df.values
        self._all_features = self._all_features_df.values

        self._train_data_len = math.ceil(len(self._all_close_prices) * 0.8)

        self._scaler = Scaler()
        self._window_size: int = config.get("window_size", 16)

        self._all_features_scaled = self._scaler.fit_transform(self._all_features)
        self._all_close_prices_scaled = self._scaler.transform(self._all_close_prices)

        self._window_size: int = config.get("window_size", 60)
        self._name = config.get("name ", "default")
        self._model = None
        self._model_path = f"{self._name}.h5"
        self._optimizer = config.get("optimizer ", "Adam")
        self._epoch_count = config.get("epoch_count", 5)
        self._batch_size = config.get("batch_size", 32)

    @staticmethod
    def filter_dataframe(df):
        return df.filter(
            ["close", "SMA7", "SMA13", "EMA", "BB_UPPER", "BB_MIDDLE", "BB_LOWER", "RSI", "ROC", "%R", "MACD",
             "SIGNAL"])

    def init_model(self):
        self._model = self._model_type(self._config)

    def step(self):
        self.init_model()

        train_data = self._all_features_scaled[0:self._train_data_len]

        x_train = []
        y_train = []

        for i in range(self._window_size, len(train_data)):
            x_train.append(train_data[i - self._window_size:i])
            y_train.append(self._all_close_prices_scaled[i:i + 1])

        x_train, y_train = np.array(x_train), np.array(y_train)
        x_train = self._model.reshape(x_train)

        self._model.compile(optimizer=self._optimizer)
        self._model.fit(x_train, y_train, batch_size=self._batch_size, epochs=self._epoch_count)

        accuracy = self.calc_accuracy(self._all_features_df)
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

    def load_model(self, model_path):
        self._model = self._model_type({})
        self._model.load(model_path)

    def trade(self, data):
        last_scaled = self._scaler.transform(data)
        x_test = [last_scaled]
        x_test = np.array(x_test)
        x_test = self._model.reshape(x_test)
        prediction = self._model.predict(x_test)
        now = x_test[0][-1][0]
        future_scaled = prediction[0][0]
        signal = Trainer.get_signal(now, future_scaled)

        prediction = self._scaler.inverse_transform(prediction)
        return prediction[0][0], signal

    def calc_rmse(self):
        test_data = self._all_features_scaled[self._train_data_len - self._window_size:]
        x_test = []
        y_test = self._all_close_prices[self._train_data_len:, :]
        for i in range(self._window_size, len(test_data)):
            x_test.append(test_data[i - self._window_size:i])

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
            correct_signal = Trainer.get_signal(now, future)

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

    @staticmethod
    def get_train_data(tiingo,symbol:str,dataprocessor:DataProcessor):
        train_data = tiingo.load_data_by_date(symbol, "2022-08-15", "2022-12-31",dataprocessor , "1hour")
        if len(train_data) == 0:
            assert False
        return train_data
