from ray.tune import Trainable
import os
import math
import numpy as np
from Data.scaler import Scaler
from Models import Saturn, BaseModel
from pandas import DataFrame
from Connectors.tiingo import Tiingo
from Data.data_processor import DataProcessor
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from pickle import dump
from Models.gan import *


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
        dataset = config.get("df")

        self._model_type = config.get("model_type", Saturn)
        self._config = config
        self._max_signal_accuracy = 0.0
        self._min_rsme = 100.0
        self._window_size: int = config.get("window_size", 16)
        self._window_size: int = config.get("window_size", 60)
        self._name = config.get("name ", "default")
        self._model = None
        self._model_path = f"{self._name}.h5"
        self._optimizer = config.get("optimizer ", "Adam")
        self._epoch_count = config.get("epoch_count", 5)
        self._batch_size = config.get("batch_size", 32)

        # Get features and target
        X_value = pd.DataFrame(dataset.iloc[:, :])
        y_value = pd.DataFrame(dataset.iloc[:, 3])

        # Normalized the data
        self._X_scaler = MinMaxScaler(feature_range=(-1, 1))
        self._y_scaler = MinMaxScaler(feature_range=(-1, 1))
        self._X_scaler.fit(X_value)
        self._y_scaler.fit(y_value)

        X_scale_dataset = self._X_scaler.fit_transform(X_value)
        y_scale_dataset = self._y_scaler.fit_transform(y_value)


        # Reshape the data
        '''Set the data input steps and output steps, 
            we use 30 days data to predict 1 day price here, 
            reshape it to (None, input_step, number of features) used for LSTM input'''
        n_steps_in = 3
        n_features = X_value.shape[1]
        n_steps_out = 1

        # Get data and check shape
        X, y, yc = self.get_X_y(X_scale_dataset, y_scale_dataset, n_steps_in, n_steps_out)
        self._X_train, X_test, = self.split_train_test(X)
        self._y_train, y_test, = self.split_train_test(y)
        self._yc_train, yc_test, = self.split_train_test(yc)
        index_train, index_test, = self.predict_index(dataset, self._X_train, n_steps_in, n_steps_out)
        # %% --------------------------------------- Save dataset -----------------------------------------------------------------

    @staticmethod
    def predict_index(dataset, X_train, n_steps_in, n_steps_out):

        # get the predict data (remove the in_steps days)
        train_predict_index = dataset.iloc[n_steps_in: X_train.shape[0] + n_steps_in + n_steps_out - 1, :].index
        test_predict_index = dataset.iloc[X_train.shape[0] + n_steps_in:, :].index

        return train_predict_index, test_predict_index

    @staticmethod
    def split_train_test(data):
        train_size = round(len(data) * 0.7)
        data_train = data[0:train_size]
        data_test = data[train_size:]
        return data_train, data_test

    @staticmethod
    def get_X_y(X_data, y_data, n_steps_in, n_steps_out):
        X = list()
        y = list()
        yc = list()

        length = len(X_data)
        for i in range(0, length, 1):
            X_value = X_data[i: i + n_steps_in][:, :]
            y_value = y_data[i + n_steps_in: i + (n_steps_in + n_steps_out)][:, 0]
            yc_value = y_data[i: i + n_steps_in][:, :]
            if len(X_value) == 3 and len(y_value) == 1:
                X.append(X_value)
                y.append(y_value)
                yc.append(yc_value)

        return np.array(X), np.array(y), np.array(yc)

    @staticmethod
    def filter_dataframe(df):
        return df.filter(
            ["close", "SMA7", "EMA", "BB_UPPER", "BB_MIDDLE", "BB_LOWER", "ROC", "%R", "MACD",
             "SIGNAL"])

    def init_model(self):
        self._model = self._model_type(self._config)

    def step(self):
        input_dim = self._X_train.shape[1]
        feature_size = self._X_train.shape[2]
        output_dim = self._y_train.shape[1]
        epoch = 100

        generator = Generator(self._X_train.shape[1], output_dim, self._X_train.shape[2],self._config )
        discriminator = Discriminator()
        gan = GAN(generator, discriminator)
        Predicted_price, Real_price, RMSPE, min_loss = gan.train(self._X_train, self._y_train, self._yc_train, epoch)

        correct = 0
        for i in range(len(Real_price)-1):
            if Real_price[i + 1] > Real_price[i] and Predicted_price[i + 1] > Predicted_price[i]:
                correct += 1
            if Real_price[i + 1] < Real_price[i] and Predicted_price[i + 1] < Predicted_price[i]:
                correct += 1

        accuracy =  100 * correct / len(Real_price)
        return {"done": False, self.METRIC: accuracy, "min_loss": min_loss}

    def _print_training_loss(self,losses):
        plt.figure(figsize=(15, 6))
        plt.cla()
        plt.plot(losses["loss"])
        plt.savefig(os.path.join(self.logdir, f"loss_{self._iteration}.png"))

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
        future_scaled = prediction[0][0]
        signal = "sell"
        if future_scaled > 0.5:
            signal = "buy"

        return signal

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

            signal = self.trade(last_prices)
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
