import os.path
from datetime import datetime
from functools import reduce
from typing import List

import pandas as pd
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

    def __init__(self,
                 symbol: str = "",
                 trades_results: List[TradeResult] = None,
                 reward: float = 0.0,
                 trades: int = 0,
                 len_df: int = 0,
                 trade_minutes: int = 0,
                 scan_time=datetime(1970, 1, 1)):
        if trades_results is None:
            trades_results = []

        self._reward = 0
        self._trades = 0
        self._wins = 0
        self._reward = reward
        self._symbol = symbol
        self._trades = trades
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
        return self.get_average_reward() > 5 and self.get_reward() > 500 and self.get_win_loss() > 0.67 and self.get_trades() >= 30

    def get_trade_df(self) -> DataFrame:
        df = DataFrame()
        for i in self._trade_results:
            df = df.append(Series(data=[i.action, i.result, i.index, self._symbol, self._indicator],
                                  index=["action", "result", "chart_index", "symbol", "indicator"]), ignore_index=True)
        return df

    def save_trade_result(self):
        self.get_trade_df().to_csv(f"{EvalResult._get_results_dir()}{self._get_trade_result_filename(self._symbol, self._indicator)}")

    @staticmethod
    def _get_results_dir():
        return f"{os.path.dirname(os.path.abspath(__file__))}\\..\\Data\\TrainResults\\"


    @staticmethod
    def is_trained(symbol:str, indicator:str) -> bool:
        return os.path.exists(f"{EvalResult._get_results_dir()}{EvalResult._get_trade_result_filename(symbol, indicator)}")

    @staticmethod
    def _get_trade_result_filename(symbol:str, indicator:str) -> str:
        return f"trade_results_{symbol}_{indicator}.csv"

    def __repr__(self):
        return f"Reward {self.get_reward()} E " + \
            f"Avg. Reqard {self.get_average_reward():.2f} E " \
            f"trade_freq {self.get_trade_frequency():.2f} " \
            f"WL {self.get_win_loss():.2f} " \
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

    def get_trade_results_as_dataframe(self) -> List[DataFrame]:
        df_list = []

        for ev_res in self._items:
            df_list.append(ev_res.get_trade_df())

        return df_list

    @staticmethod
    def get_indicator_names(df_list:List[DataFrame]) -> List[str]:
        indicator_names = []
        for df in df_list:
            indicator_names.append(df.iloc[0].indicator)

        return indicator_names


    @staticmethod
    def calc_combination(dataframes: List[DataFrame]):
        try:
            # Merge all dataframes on 'chart_index' and keep only common indices
            merged_df = reduce(lambda left, right: pd.merge(left, right, on='chart_index', suffixes=('', '_r')), dataframes)
            if len(merged_df) == 0:
                return merged_df


            # Get columns related to 'action'
            action_columns = [col for col in merged_df.columns if col.startswith('action')]

            # Filter rows where all actions are the same and not 'both'
            common_actions = merged_df[action_columns].apply(lambda row: row.nunique() == 1 and row.iloc[0] != 'both',
                                                             axis=1)
            result_df = merged_df[common_actions]

            # Create the result DataFrame with required columns
            result = pd.DataFrame({
                'action': result_df[action_columns[0]],
                'index': result_df['chart_index']
            })
        except Exception as e:
            print("Error creating")

        return result

    @staticmethod
    def combine_signals(dataframes: List[DataFrame]):
        common_indices = list(reduce(lambda x, y: x.intersection(y), [set(df["chart_index"]) for df in dataframes]))
        common_indices.sort()
        signal_combinations = []
        for i in common_indices:
            actions = []
            for df in dataframes:
                v = df[df.chart_index == i]
                action = v["action"].item()
                if action != "both":
                    actions.append(action)

            if len(actions) > 0 and len(set(actions)) == 1:
                signal_combinations.append({"index": i, "action": actions[0]})

        return DataFrame(signal_combinations)

    @staticmethod
    def final_simulation(combined_signals_df: DataFrame, buy_simulation: DataFrame):
        common_indices = list(reduce(lambda x, y: x.intersection(y), [set(df["chart_index"]) for df in dataframes]))
        common_indices.sort()
        signal_combinations = []
        for i in common_indices:
            actions = []
            for df in dataframes:
                v = df[df.chart_index == i]
                action = v["action"].item()
                if action != "both":
                    actions.append(action)

            if len(actions) > 0 and len(set(actions)) == 1:
                signal_combinations.append({"index": i, "action": actions[0]})

        return DataFrame(signal_combinations)







    def __repr__(self):
        text = f"Avg Win_loss {self.get_avg_profit()} \r\n"
        text += f"Avg Trades {self.get_avg_trades()}"

        return text
