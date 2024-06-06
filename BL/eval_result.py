import os.path
from datetime import datetime
from functools import reduce
from typing import List

from pandas import Series, DataFrame

from BL.datatypes import TradeAction


class TradeResult:
     def __init__(self, action: str, result: float, index: int):
         self.action:str = action
         self.result:float  = result
         self.index: int = index



class EvalResult:

    def __init__(self,
                 trades_results:List = [],
                 reward: float = 0.0,
                 trades: int = 0,
                 len_df: int = 0,
                 trade_minutes: int = 0,
                 wins: int = 0,
                 scan_time = datetime(1970, 1, 1),
                 symbol: str = "",
                 indicator:str = "" ):
        self._reward = reward
        self._symbol = symbol
        self._trades = trades
        self._len_df = len_df
        self._trade_minutes = trade_minutes
        self._scan_time = scan_time
        self._wins = wins
        self._trade_results:List = trades_results
        self._indicator = indicator

    def get_reward(self):
        return self._reward

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
        return self.get_average_reward() > 5 and self.get_reward() > 100 and self.get_win_loss() > 0.7 and self.get_trades() >= 10

    def get_trade_df(self) -> DataFrame:
        df = DataFrame()
        for i in self._trade_results:
            df = df.append(Series(data=[i.action, i.result, i.index, self._symbol, self._indicator],
                                  index=["action", "result", "chart_index", "symbol", "indicator"]), ignore_index=True)
        return df

    def save_trade_result(self):
        self.get_trade_df().to_csv(f".\\Data\\TrainResults\\{self._get_trade_result_filename(self._symbol, self._indicator)}")

    @staticmethod
    def is_trained(symbol:str, indicator:str) -> bool:
        return os.path.exists(f".\\Data\\TrainResults\\{EvalResult._get_trade_result_filename(symbol, indicator)}")

    @staticmethod
    def _get_trade_result_filename(symbol:str, indicator:str) -> str:
        return f"trade_results_{symbol}_{indicator}.csv"

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
        common_indices = list(reduce(lambda x, y: x.intersection(y), [set(df["chart_index"]) for df in dataframes]))
        common_indices.sort()
        overall_reward = 0
        for i in common_indices:
            #print(f"Calc indice {i}")
            actions = []
            reward = 0
            for df in dataframes:
                v = df[df.chart_index == i]
                action = v["action"].item()
                if action != "both":
                    #print(f"Action {action}")
                    actions.append(action)
                    reward = v["result"].item()

            if len(actions) > 0 and len(set(actions)) == 1:
                #print(f"Trade at {i}")
                overall_reward = overall_reward + reward


        return overall_reward







    def __repr__(self):
        text = f"Avg Win_loss {self.get_avg_profit()} \r\n"
        text += f"Avg Trades {self.get_avg_trades()}"

        return text
