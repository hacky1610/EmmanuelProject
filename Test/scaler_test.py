from Data.scaler import Scaler
import unittest
import numpy as np

class ScalerTest(unittest.TestCase):

    train_array = np.array([[1,2,4], [3, 4,1]])
    def test_fit(self):
        s = Scaler()
        s.fit(self.train_array)
        assert s._max == 4
        assert s._min == 1

    def test_transform(self):
        s = Scaler()
        s.fit(self.train_array)
        res = s.transform(self.train_array)
        assert res[1][0] == 0.75

    def test_fit_transform(self):
        s = Scaler()
        res = s.fit_transform(self.train_array)
        assert res[1][0] == 0.75

    def test_inverse_transform(self):
        s = Scaler()
        scaled = s.fit_transform(self.train_array)
        original = s.inverse_transform(scaled)
        assert original[0][0] == 1
        assert (original == self.train_array).all()