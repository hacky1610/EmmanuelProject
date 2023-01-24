import gym
from enum import Enum
from pandas import DataFrame, Series
from Connectors.IG import IG
from gym import spaces
import numpy as np


class Actions(Enum):
    Sell = 0
    Buy = 1


class IgEnv(gym.Env):

    def __init__(self,config: dict):
        self.tracer = config["tracer"]
        self.df = config["df"]
        self.window_size = config["window_size"]

        self.prices, self.times, self.signal_features = self._process_data()
        self.shape = (self.window_size, self.signal_features.shape[1])

        # spaces
        self.action_space = spaces.Discrete(len(Actions))
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=self.shape, dtype=np.float64)

        #IG
        self.ig = IG()

        self.symbol = "CS.D.GBPUSD.CFD.IP"

    def _process_data(self):
        prices = self.df.loc[:, 'Close'].to_numpy()
        times = self.df.index.to_numpy()
        signal_features = self.df.loc[:, ['Low', 'SMA', 'RSI', 'ROC', '%R', 'MACD', 'SIGNAL']].to_numpy()
        return prices, times, signal_features

    def reset(self):
        return self._get_observation()

    def step(self, action):
        if action == Actions.Buy.value:
            self.ig.buy(self.symbol)
        else:
            if self.ig.has_opened_positions():
                deal = self.ig.get_opened_position_id()
                self.ig.sell(deal)

    def _get_observation(self):
        return self.signal_features[(len(self.signal_features) - self.window_size + 1):]



