import numpy as np

from Envs.tradingEnv import TradingEnv, Actions, Positions
from ray.rllib.env.env_context import EnvContext

class ForexEnv(TradingEnv):

    def __init__(self, config: dict):
        super().__init__(config["df"], config["window_size"])

        self.spread = 0.0005 # unit
        self.tracer = config["tracer"] #TODO: Add tracer to parent class


    def _process_data(self):
        prices = self.df.loc[:, 'Close'].to_numpy()
        signal_features = self.df.loc[:, ['Low', 'SMA', 'RSI', 'ROC', '%R', 'MACD', 'SIGNAL']].to_numpy()
        return prices, signal_features


    def _calculate_reward(self, action):
        step_reward = 0
        trade = False
        if ((action == Actions.Buy.value and self._position == Positions.Short) or
            (action == Actions.Sell.value and self._position == Positions.Long)):
            trade = True

        if trade:
            current_price = self.prices[self._current_tick]
            last_trade_price = self.prices[self._last_trade_tick]
            price_diff = current_price - last_trade_price #Todo: gebühr

            if self._position == Positions.Long:
                step_reward += price_diff
        return step_reward


    def _update_profit(self, action):
        trade = False
        if ((action == Actions.Buy.value and self._position == Positions.Short) or
            (action == Actions.Sell.value and self._position == Positions.Long)):
            trade = True

        if trade or self._done:
            current_price = self.prices[self._current_tick]
            last_trade_price = self.prices[self._last_trade_tick]

            current_price = current_price * (1-self.spread)
            if self._position == Positions.Long:
                shares = self._total_profit / last_trade_price
                self._total_profit = shares * current_price



    def max_possible_profit(self):
        current_tick = self._start_tick
        last_trade_tick = current_tick - 1
        profit = 1.

        while current_tick <= self._end_tick:
            position = None
            if self.prices[current_tick] < self.prices[current_tick - 1]:
                while (current_tick <= self._end_tick and
                       self.prices[current_tick] < self.prices[current_tick - 1]):
                    current_tick += 1
                position = Positions.Short
            else:
                while (current_tick <= self._end_tick and
                       self.prices[current_tick] >= self.prices[current_tick - 1]):
                    current_tick += 1
                position = Positions.Long

            if position == Positions.Long:
                current_price = self.prices[current_tick - 1]
                last_trade_price = self.prices[last_trade_tick]
                shares = profit / last_trade_price
                profit = shares * current_price
            last_trade_tick = current_tick - 1

        return profit