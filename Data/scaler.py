import numpy as np
class Scaler:
    _min:float
    _max:float

    def fit(self,array:np.array):
        self._min = array.min().min()
        self._max = array.max().max()

    def transform(self,array:np.array):
        return array / self._max

    def fit_transform(self,array:np.array):
        self.fit(array)
        return self.transform(array)

    def inverse_transform(self,array):
        return array * self._max


s = Scaler()
a = np.array([[1,2],[2,4]])
s.fit(a)
s.transform(a)
s.inverse_transform(1)