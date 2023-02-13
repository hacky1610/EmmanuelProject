from Models.BaseModel import BaseModel
from keras.models import Sequential
from keras.layers import LSTM, Dense, TimeDistributed, BatchNormalization, Flatten
from keras.layers.convolutional import Conv1D, MaxPooling1D
import numpy as np
from ray import tune


class Venus(BaseModel):

    def __init__(self, config: dict):
        super().__init__(config)
        self._td1_len = config.get("td1_len", 128)
        self._td2_pool_size = config.get("td2_pool_size", 2)
        self._td3_len = config.get("td3_len", 128)
        self._lstm1_len = config.get("lstm1_len", 50)
        self._lstm2_len = config.get("lstm2_len ", 50)
        self._dens_len = config.get("dense_len ", 25)

        self._model = self._create()

    def reshape(self, array):
        return np.reshape(array, (len(array), 1, self._window_size, self._num_features))

    def _create(self):
        model = Sequential()
        model.add(TimeDistributed(Conv1D(filters=self._td1_len, kernel_size=1, activation='relu'),
                                  input_shape=(None, self._window_size, self._num_features)))
        model.add(TimeDistributed(MaxPooling1D(pool_size=self._td2_pool_size, strides=None)))
        model.add(TimeDistributed(Conv1D(filters=self._td3_len, kernel_size=1, activation='relu')))
        model.add(TimeDistributed(Flatten()))
        model.add(LSTM(self._lstm1_len, return_sequences=True))
        model.add(LSTM(self._lstm2_len))
        model.add(BatchNormalization())
        model.add(Dense(1))
        return model

    @staticmethod
    def get_tuner():
        return {
            "lstm1_len": tune.grid_search([64, 128, 256]),
            "lstm2_len": tune.grid_search([64, 128, 256]),
            "dense_len": 16,
            "td1_len": tune.grid_search([64, 128, 256]),
            "td3_len": tune.grid_search([64, 128, 256]),
            "td2_pool_size": tune.grid_search([2, 4, 8]),
        }
