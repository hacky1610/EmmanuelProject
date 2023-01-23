import gym
from gym import spaces
from gym.utils import seeding
import numpy as np
from enum import Enum
from matplotlib import pyplot as plt
from pandas import DataFrame, Series
import os

class Actions(Enum):
    Sell = 0
    Buy = 1


class Positions(Enum):
    Short = 0
    Long = 1

    def opposite(self):
        return Positions.Short if self == Positions.Long else Positions.Long


class TradingEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self, df: DataFrame, window_size):
        assert df.ndim == 2

        self.seed()
        self.df = df
        self.window_size = window_size
        self.prices, self.times, self.signal_features = self._process_data()
        self.shape = (window_size, self.signal_features.shape[1])

        # spaces
        self.action_space = spaces.Discrete(len(Actions))
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=self.shape, dtype=np.float64)

        # episode
        self._start_tick = self.window_size
        self._end_tick = len(self.prices) - 1
        self._done = None
        self._current_tick = None
        self._last_trade_tick = None  # TODO: should be removed
        self._position = None
        self._position_history = None
        self._trade_history = None
        self._total_reward = None
        self._total_profit = None
        self.history = None

    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def reset(self):
        self._done = False
        self._current_tick = self._start_tick
        self._last_trade_tick = self._current_tick - 1
        self._position = Positions.Short
        self._position_history = (self.window_size * [None]) + [self._position]  # TODO:?
        self._trade_history = {}
        self._total_reward = 0.
        self._total_profit = 1.  # unit
        self.history = {}
        return self._get_observation()

    def add_to_history(self, tick: int, price: float, date: str, action: Actions):
        self._trade_history[tick] = {
            "Date":date,
            "Price":price,
            "Action":action
        }

    def plot(self, folder: str, file_name:str = "graph.png"):
        plt.figure(figsize=(15, 6))
        plt.cla()
        self.render_all()
        plt.savefig(os.path.join(folder,file_name))

    def step(self, action):
        self._done = False
        self._current_tick += 1

        if self._current_tick == self._end_tick:
            self.tracer.write(f"Reward: {self._total_reward} Profit: {self._total_profit}")
            self._done = True

        step_reward = self._calculate_reward(action)
        self._total_reward += step_reward
        self._update_profit(action)

        trade = False
        if ((action == Actions.Buy.value and self._position == Positions.Short) or
                (action == Actions.Sell.value and self._position == Positions.Long)):
            trade = True

        if trade:
            self._position = self._position.opposite()
            self._last_trade_tick = self._current_tick
            self.add_to_history(self._current_tick, self.get_current_price(), self.get_current_date(), action)

        self._position_history.append(self._position)
        observation = self._get_observation()
        info = dict(
            total_reward=self._total_reward,
            total_profit=self._total_profit,
            position=self._position.value
        )
        self._update_history(info)

        return observation, step_reward, self._done, info

    def get_report(self) -> str:
        text = ""
        lastBuy = 0
        for key,value in self._trade_history.items():  # Todo: GetIndexes from Value
            if value["Action"] == Actions.Buy.value:
                lastBuy = value['Price']
                text += f"{value['Date']} - Buy by {value['Price']} \n"
            else:
                diff = value['Price'] - lastBuy
                if diff >= 0:
                    result = "WON"
                else:
                    result = "LOST"
                text += f"{value['Date']} - Sell by {value['Price']} - {result}: {diff}\n"
        return text

    def save_report(self,folder:str):
        with open(os.path.join(folder,"report.txt"), "a") as f:
            f.write(self.get_report())

    def _get_observation(self):
        return self.signal_features[(self._current_tick - self.window_size + 1):self._current_tick + 1]

    def _update_history(self, info):
        if not self.history:
            self.history = {key: [] for key in info.keys()}

        for key, value in info.items():
            self.history[key].append(value)

    def render_all(self, mode='human'):
        plt.plot(self.prices)
        buy_ticks = []
        sell_ticks = []

        for key,value in self._trade_history.items():  # Todo: GetIndexes from Value
            if value["Action"] == Actions.Buy.value:
                buy_ticks.append(key)
            else:
                sell_ticks.append(key)

        # Markers: https://matplotlib.org/stable/gallery/lines_bars_and_markers/marker_reference.html#sphx-glr-gallery-lines-bars-and-markers-marker-reference-py
        plt.plot(sell_ticks, self.prices[sell_ticks], 'ro')
        plt.plot(buy_ticks, self.prices[buy_ticks], 'go')

        plt.suptitle(
            "Total Reward: %.6f" % self._total_reward + ' ~ ' +
            "Total Profit: %.6f" % self._total_profit
        )

    def close(self):
        plt.close()

    def save_rendering(self, filepath):
        plt.savefig(filepath)

    def pause_rendering(self):
        plt.show()

    def _process_data(self):
        raise NotImplementedError

    def _calculate_reward(self, action):
        raise NotImplementedError

    def _update_profit(self, action):
        raise NotImplementedError

    def max_possible_profit(self):  # trade fees are ignored
        raise NotImplementedError

    def get_current_price(self):
        return self.prices[self._current_tick]

    def get_current_date(self):
        return self.times[self._current_tick]

    def get_last_trade_price(self):
        return self.prices[self._last_trade_tick]
