import datetime
import unittest
from Agents.Renotte import Renotte
from unittest.mock import MagicMock
from Envs.stocks_env import StocksEnv
import pandas as pd


class RenotteTest(unittest.TestCase):
    plt = MagicMock()

    def test_Init(self):
        ag = Renotte(self.plt)

    def test_Rand(self):
        df = pd.DataFrame(data={'Date': [1, 2, 3 , 4,5,6], 'Close': [3, 4,5,2,2,2], 'Open': [3, 4,5,2,2,2]})
        df.set_index("Date", inplace=True)
        env = StocksEnv(df,window_size=2, frame_bound=(2, 4))
        ag = Renotte(self.plt)
        ag.doRandTest(env)
