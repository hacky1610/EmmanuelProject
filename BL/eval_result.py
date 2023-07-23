class EvalResult:

    def __init__(self, reward: float, trades: int, len_df: int, trade_minutes: int, wins: int):
        self._reward = reward
        self._trades = trades
        self._len_df = len_df
        self._trade_minutes = trade_minutes
        self._wins = wins

    def get_reward(self):
        return self._reward

    def get_trades(self):
        return self._trades

    def get_average_reward(self):
        if self._trades == 0:
            return 0
        return round(self._reward / self._trades, 7)

    def get_trade_frequency(self):
        if self._len_df == 0:
            return 0
        return round(self._trades / self._len_df, 7)

    def get_win_loss(self):
        if self._trades == 0:
            return 0
        return round(self._wins / self._trades, 7)

    def get_average_minutes(self):
        if self._trades == 0:
            return 0
        return round(self._trade_minutes / self._trades, 7)

    def __repr__(self):
        return f"Reward {self.get_reward()}, \
                success {self.get_average_reward()}, \
                trade_freq {self.get_trade_frequency()}, \
                win_loss {self.get_win_loss()}, \
                trades {self.get_trades()}, \
                avg_minutes {self.get_average_minutes()}"
