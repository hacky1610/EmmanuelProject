import os.path
import traceback
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

    def get_trading_hours(self) -> float:
        if self.close_time == "" or self.open_time == "":
            return 0

        c = datetime.strptime(self.close_time, '%Y-%m-%dT%H:%M:%S.%fZ')
        o = datetime.strptime(self.open_time, '%Y-%m-%dT%H:%M:%S.%fZ')
        e = c - o
        return e.total_seconds() / 3600

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

    def __str__(self):
        return f"Action {self.action} Open {self.open_time} {self.opening} Close {self.close_time} {self.closing} Profit {self.profit} ISL {self.intelligent_stop_used}"

class EvalResult:

    def __init__(self,
                 symbol: str = "",
                 trades_results: List[TradeResult] = None,
                 reward: float = 0.0,
                 trades: int = 0,
                 len_df: int = 0,
                 trade_minutes: int = 0,
                 avg_trading_hours: float = 0,
                 scan_time=datetime(1970, 1, 1),
                 adapted_isl_distance: bool = False,
                 avg_won_result: float = 0,
                 avg_lost_result: float = 0):
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
        self._adapted_isl_distance = adapted_isl_distance

        for trade in trades_results:
            self._reward += trade.profit
            if trade.won():
                self._wins += 1
        self._trades = len(trades_results)

        df = self.get_trade_df()
        self._avg_won_result = avg_won_result
        self._avg_lost_result = avg_lost_result
        self._avg_trading_hours = avg_trading_hours

        if len(df) > 0:
            self._avg_won_result = df.result[df.result > 0].mean()
            self._avg_lost_result = df.result[df.result < 0].mean()
            self._avg_trading_hours = df.trading_hours.median()

    def set_result(self, reward, trades, wins):
        self._reward = reward
        self._trades = trades
        self._wins = wins

    def is_better(self, compare_to) -> bool:
        return EvalResult.compare(self.get_win_loss(),self.get_reward(),
                                  compare_to.get_win_loss(), compare_to.get_reward())

    @staticmethod
    def compare(wl1, reward1, wl2, reward2):
        if (wl1 >= 0.95 and wl2 >= 0.95 and abs(wl1 - wl2) <= 0.03) or wl1 == wl2:
            return reward2 > reward1
        else:
            return wl2 > wl1


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

    def get_avg_win(self):
        return self._avg_won_result

    def get_avg_lost(self):
        return self._avg_lost_result

    def get_avg_trading_hours(self):
        return self._avg_trading_hours

    def get_avg_win_lost(self):
        return self._avg_won_result + self._avg_lost_result

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
            self.get_win_loss(),
            self._adapted_isl_distance,
            self._avg_lost_result,
            self._avg_won_result,
            self._avg_trading_hours
        ],
            index=["_reward",
                   "_trades",
                   "_wins",
                   "_len_df",
                   "_trade_minutes",
                   "_scan_time",
                   "_wl",
                   "_adapted_isl_distance",
                   "_avg_lost_result",
                   "_avg_won_result",
                   "_avg_trading_hours"
                   ])

    def is_good(self):
        check1 = (self.get_win_loss() >= 0.75 and self.get_trades() >= 70 and
                  self.get_avg_trading_hours() != 0 and self.get_avg_trading_hours() < 48)
        return check1

    def get_trade_df(self) -> DataFrame:
        df = DataFrame()
        for i in self._trade_results:
            df = df.append(Series(data=[i.action, i.profit, self._symbol, i.get_trading_hours()],
                                  index=["action", "result",  "symbol", "trading_hours"]), ignore_index=True)
        return df

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
            f"Average {self.get_average_reward():.2f} E " \
            f"Avg Won {self.get_avg_win():.2f} E " \
            f"Avg Lost {self.get_avg_lost():.2f} E " \
            f"Avg hours {self.get_avg_trading_hours():.2f} " \
            f"WL {self.get_win_loss():.2f} " \
            f"trades {self.get_trades()} "

    def to_dict_foo(self):
        return {
            "trades": self.get_trades(),
            "wl": self.get_win_loss()
        }


class EvalResultCollection:

    def __init__(self):
        self._items = []


    def add(self, r: EvalResult):
        self._items.append(r)

    def get_avg_profit(self):
        df = pd.DataFrame([obj.to_dict_foo() for obj in self._items])
        df = df[df.trades != 0]

        return df.wl.median()

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
    def remove_empty_dataframes(df_list):
        """
        Entfernt leere DataFrames aus einer Liste von DataFrames.

        :param df_list: List of pandas DataFrames
        :return: List of pandas DataFrames with non-empty DataFrames only
        """
        return [df for df in df_list if not df.empty]

    @staticmethod
    def calc_combination(dataframes: List[DataFrame]):
        try:
            # Merge all dataframes on 'chart_index' and keep only common indices
            dataframes = EvalResultCollection.remove_empty_dataframes(dataframes)
            merged_df = reduce(lambda left, right: pd.merge(left, right, on='chart_index', suffixes=('', '_r')), dataframes)
            if len(merged_df) == 0:
                return merged_df

            action_columns = [col for col in merged_df.columns if col.startswith('action')]

            # Define a function to check if actions are the same or contain "both"
            def is_valid_combination(row):
                if 'none' in row.values:
                    return False

                actions = [action for action in row if action != TradeAction.BOTH]
                return len(set(actions)) <= 1

            # Filter rows based on the custom function
            valid_combinations = merged_df[action_columns].apply(is_valid_combination, axis=1)
            result_df = merged_df[valid_combinations]

            def determine_action(row):
                for action in row:
                    if action != "both":
                        return action
                return "both"  # Fallback if all are "both"

            result_df['final_action'] = result_df[action_columns].apply(determine_action, axis=1)

            # Create the result DataFrame with required columns
            result = pd.DataFrame({
                'action': result_df['final_action'],
                'index': result_df['chart_index']
            })
        except Exception as e:
            traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
            print(f"Exception: {e} File:{traceback_str}")

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




    def __repr__(self):
        text = f"Avg Win_loss {self.get_avg_profit()} \r\n"
        text += f"Avg Trades {self.get_avg_trades()}"

        return text
