from ray.tune import Trainable
from Utils import Utils
import os
import math
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from keras.models import Sequential
from keras.layers import LSTM,Dense
import matplotlib.pyplot as plt

class LSTM_Trainer(Trainable):
    METRIC = "signal_accuracy"

    def setup(self, config):
        df = config.get("df")
        self._best_signal_accuracy = 0.0
        self._all_data_df = df.filter(["close"])
        self._all_data = self._all_data_df.values
        self._train_data_len = math.ceil(len(self._all_data) * 0.8)

        self._scaler = MinMaxScaler(feature_range=(0, 1))
        self._all_data_scaled = self._scaler.fit_transform(self._all_data)
        self._window_size:int = config.get("window_size",60)
        self._lstm1_len = config.get("lstm1_len",50)
        self._lstm2_len = config.get("lstm2_len ",50)
        self._dens_len = config.get("dense_len ",25)
        self._name = config.get("name ","default")
        self._model = None
        self._model_path = f"{self._name}.h5"
        self._optimizer = config.get("optimizer ","Adam")

    @staticmethod
    def create_model(data_len, lstm1_len: int, lstm2_len: int, dens_len: int):
        model = Sequential()
        model.add(LSTM(lstm1_len, return_sequences=True, input_shape=(data_len, 1)))
        model.add(LSTM(lstm2_len, return_sequences=False))
        model.add(Dense(dens_len))
        model.add(Dense(1))
        return model


    def step(self):
        train_data = self._all_data_scaled[0:self._train_data_len, :]

        x_train = []
        y_train = []

        for i in range(self._window_size, len(train_data)):
            x_train.append(train_data[i - self._window_size:i, 0])
            y_train.append(train_data[i, 0])

        x_train, y_train = np.array(x_train), np.array(y_train)
        x_train = np.reshape(x_train, (x_train.shape[0], x_train.shape[1], 1))

        self._model = LSTM_Trainer.create_model(x_train.shape[1], 50, 50, 25)

        self._model.compile(optimizer=self._optimizer, loss="mean_squared_error")
        self._model.fit(x_train, y_train, batch_size=1, epochs=1)

        accuracy = self.calc_accuracy(self._all_data_df )
        if accuracy > self._best_signal_accuracy:
            self._model.save(os.path.join(self.logdir,f"model_{self._iteration}.h5"))
            self._best_signal_accuracy = accuracy

        return {"done": False, self.METRIC: accuracy, "rmse":self.calc_rmse()}

    def save_model(self):
        self._model.save(self._model_path )

    def load_model(self):
        self._model = LSTM_Trainer.create_model(self._window_size,self._lstm1_len,self._lstm2_len,self._dens_len)
        self._model.load_weights(self._model_path )

    def trade(self, model, data):

        last_scaled = self._scaler.transform(data)
        X_test = []
        X_test.append(last_scaled)
        X_test = np.array(X_test)
        X_test = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], 1))
        pred = model.predict(X_test)
        now = X_test[0][-1][0]
        futureScaled = pred[0][0]
        signal = LSTM_Trainer.get_signal(now, futureScaled)

        pred = self._scaler.inverse_transform(pred)
        return pred[0][0], signal

    def calc_rmse(self):
        test_data = self._all_data_scaled[self._train_data_len - self._window_size: , :]
        x_test = []
        y_test = self._all_data[self._train_data_len: , :]
        for i in range (self._window_size,len(test_data)):
            x_test.append(test_data[i-self._window_size:i,0])

        x_test = np.array(x_test)
        x_test = np.reshape(x_test,(x_test.shape[0],x_test.shape[1],1))
        predictions = self._model.predict(x_test)
        predictions = self._scaler.inverse_transform(predictions)
        return  np.sqrt(np.mean(predictions - y_test)**2)

    def calc_accuracy(self, close_prices):
        correctSignals = 0
        incorrectSignals = 0

        for i in range(1, 30):
            last_prices = close_prices[-self._window_size - i:-i].values
            future = close_prices.to_numpy()[-i][0]
            now = close_prices.to_numpy()[-i - 1][0]

            prediction, signal = self.trade(self._model, last_prices)
            correct_signal = LSTM_Trainer.get_signal(now, future)

            if correct_signal == signal:
                correctSignals += 1
            else:
                incorrectSignals += 1

        return 100 * correctSignals / (correctSignals + incorrectSignals)

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