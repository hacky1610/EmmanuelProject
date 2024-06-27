from datetime import datetime
from typing import List

from pandas import Series, DataFrame

from BL.datatypes import TradeAction


class TradeResult:
    def __init__(self, action: str = TradeAction.NONE,
                 open_time: str = "", opening: float = 0):
        self.action: str = action
        self.open_time = open_time
        self.opening: float = opening
        self.close_time = ''
        self.profit: float = 0
        self.closing: float = 0
        self.intelligent_stop_used: bool = False

    def set_result(self, closing: float, close_time: str, profit: float):
        self.closing = closing
        self.close_time = close_time
        self.profit = profit

    def set_intelligent_stop_used(self):
        self.intelligent_stop_used = True

    def won(self) -> bool:
        return self.profit > 0

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "open_time": self.open_time,
            "opening": self.opening,
            "close_time": self.close_time,
            "profit": self.profit,
            "closing": self.closing,
            "won": self.won(),
            "intelligent_stop_used": self.intelligent_stop_used
        }

class EvalResult:

    def __init__(self, trades_results: List[TradeResult] = None,
                 len_df: int = 0,
                 trade_minutes: int = 0,
                 scan_time=datetime(1970, 1, 1)):
        if trades_results is None:
            trades_results = []

        self._reward = 0
        self._trades = 0
        self._wins = 0
        self._len_df = len_df
        self._trade_minutes = trade_minutes
        self._scan_time = scan_time
        self._trade_results = trades_results

        for trade in trades_results:
            self._reward += trade.profit
            if trade.won():
                self._wins += 1
        self._trades = len(trades_results)

    def set_result(self, reward, trades, wins):
        self._reward = reward
        self._trades = trades
        self._wins = wins


    def get_reward(self):
        return self._reward

    def get_trade_results(self) -> List[TradeResult]:
        return self._trade_results

    def get_trade_result_df(self) -> DataFrame:
        l = []
        for trade in self._trade_results:
            l.append(trade.to_dict())

        return DataFrame(l)

    def get_trades(self) -> int:
        return self._trades

    def get_scan_time(self) -> datetime:
        return self._scan_time

    def get_average_reward(self):
        if self._trades == 0:
            return 0
        return round(self._reward / self._trades, 7)

    def get_trade_frequency(self):
        if self._len_df == 0:
            return 0
        return round(self._trades / self._len_df, 7)

    def get_win_loss(self) -> float:
        if self._trades == 0:
            return 0
        return round(self._wins / self._trades, 7)

    def get_average_minutes(self):
        if self._trades == 0:
            return 0
        return round(self._trade_minutes / self._trades, 7)

    def get_data(self) -> Series:
        return Series([
            self._reward,
            self._trades,
            self._wins,
            self._len_df,
            self._trade_minutes,
            self._scan_time,
            self.get_win_loss()
        ],
            index=["_reward",
                   "_trades",
                   "_wins",
                   "_len_df",
                   "_trade_minutes",
                   "_scan_time",
                   "_wl"
                   ])

    def is_good(self):
        return self.get_average_reward() > 5 and self.get_reward() > 100 and self.get_win_loss() > 0.4 and self.get_trades() >= 10

    def __repr__(self):
        return f"Reward {self.get_reward()} E " + \
            f"Avg. Reqard {self.get_average_reward()} E " \
            f"trade_freq {self.get_trade_frequency()} " \
            f"WL {self.get_win_loss()} " \
            f"trades {self.get_trades()} " \
            f"avg_minutes {self.get_average_minutes()} "


class EvalResultCollection:

    def __init__(self):
        self._items = []


    def add(self, r: EvalResult):
        self._items.append(r)

    def get_avg_profit(self):
        win_loss_overall = 0
        market_measures = 0
        for i in self._items:
            if i.get_trades() != 0:
                market_measures = market_measures + 1
                win_loss_overall = win_loss_overall + i.get_win_loss()
        if market_measures == 0:
            return 0

        return win_loss_overall / market_measures

    def get_avg_trades(self):
        win_loss_trades = 0
        market_measures = 0
        for i in self._items:
            if i.get_trades() != 0:
                market_measures = market_measures + 1
                win_loss_trades = win_loss_trades + i.get_trades()

        if market_measures == 0:
            return 0

        return win_loss_trades / market_measures

    def __repr__(self):
        text = f"Avg Win_loss {self.get_avg_profit()} \r\n"
        text += f"Avg Trades {self.get_avg_trades()}"

        return text
