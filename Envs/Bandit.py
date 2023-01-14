import gym
import pandas as np
from gym.spaces import Discrete, Box
from gym.utils import seeding

class Bandit(gym.Env):

    def __init__(self,df):
        self.max_inflation = np.array([[100.]])
        self.action_space = Discrete(3)
        self.observation_space = Box(-self.max_inflation, self.max_inflation)
        self.portfolio = 0
        self.trade_amount_per_step = 100.
        self.money_invested
        self.df = df

    def reset(self):
        self.index = 0
        self.done = False
        self.info = {}

        return np.array([[0.]])

    def get_portfolio_value(self,row):
        return -1

    def _process_data(self):
        prices = self.df.loc[:, 'Close'].to_numpy()

        prices[self.frame_bound[0] - self.window_size]  # validate index (TODO: Improve validation)
        prices = prices[self.frame_bound[0] - self.window_size:self.frame_bound[1]]

        diff = np.insert(np.diff(prices), 0, 0)
        signal_features = np.column_stack((prices, diff))

        return prices, signal_features

    def step(self, action):
        if self.done:
            reward = 0
            regret = 0
        else:
            price = self.prices[self.index]
            before = self.portfolio
            asset_to_trade_fraction = self.trade_amount_per_step / price

            if action == 0: #Buy
                self.portfolio += asset_to_trade_fraction
                self.money_investet += self.trade_amount_per_step
            elif action == 1: #Sell
                self.portfolio -= asset_to_trade_fraction

            reward = float(before - self.portfolio)/20000
            self.index += 1

            if self.index >= len(self.df):
                self.done = True

            self.info = {
                "regret":0.,
                "index": self.index
            }

            return [np.arry([[0.]]),reward,self.done,self.info]

