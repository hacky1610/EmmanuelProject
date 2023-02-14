import numpy as np


class Scaler:
    _min: float
    _max: float

    def fit(self, array: np.array):
        self._min = array.min().min()
        self._max = array.max().max()

    def transform(self, array: np.array) -> np.ndarray:
        return array / self._max

    def fit_transform(self, array: np.array) -> np.ndarray:
        self.fit(array)
        return self.transform(array)

    def inverse_transform(self, array):
        return array * self._max



