from Models.BaseModel import BaseModel
from keras.models import Sequential
from keras.layers import LSTM, Dense
import numpy as np
from ray import tune


class Saturn(BaseModel):

    def __init__(self, config: dict):
        super().__init__(config)
        self._lstm1_len = config.get("lstm1_len", 64)
        self._lstm2_len = config.get("lstm2_len ", 64)
        self._dens_len = config.get("dense_len ", 16)
        self._model = self._create()

    def _create(self):
        model = Sequential()
        model.add(LSTM(units=self._lstm1_len,
                       return_sequences=True,
                       input_shape=(self._window_size, self._num_features)))
        model.add(LSTM(units=self._lstm2_len,
                       return_sequences=False))
        model.add(Dense(self._dens_len))
        model.add(Dense(1))
        return model

    def reshape(self, arr):
        return np.reshape(arr, (len(arr), self._window_size, self._num_features))

    @staticmethod
    def get_tuner():
        return {
            "lstm1_len": 64,
            "lstm2_len": 64,
            "dense_len": 16,
        }
