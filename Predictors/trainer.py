import pandas as pd
from pandas import DataFrame, Series
import random
from Predictors.rsi_stoch import RsiStoch
from Predictors.rsi_bb import RsiBB
import itertools


class Trainer:

    def __init__(self, analytics):
        self._analytics = analytics

    def _rsi_trainer(self, version: str):

        json_objs = []
        for rsi_upper, rsi_lower, trend in itertools.product(list(range(65, 80, 3)), list(range(20, 35, 3)),
                                                             [.005, .01, .03, .05]):
            json_objs.append({
                "rsi_upper_limit": rsi_upper,
                "rsi_lowe_limit": rsi_lower,
                "rsi_trend": trend,
                "version": version
            })
        return json_objs

    def _BB_trainer(self, version: str):

        json_objs = []
        for p1, p2, peaks in itertools.product(
                list(range(1, 5)),
                list(range(1, 5)),
                list(range(0, 4))):
            json_objs.append({
                "period_1": p1,
                "period_2": p2,
                "peak_count": peaks,
                "version": version
            })
        return json_objs

    def _stop_limt_trainer(self, version: str):

        json_objs = []
        for stop, limit in itertools.product(
                [1.8, 2.0, 2.3, 2.7, 3.],
                [1.8, 2.0, 2.3, 2.7, 3.]):
            json_objs.append({
                "stop": stop,
                "limit": limit,
                "version": version
            })
        return json_objs

    def _BB_change_trainer(self, version: str):

        json_objs = []
        for change in [0.0,0.01,0.05, 0.1, 0.3, .5]:
            json_objs.append({
                "bb_change": change,
                "version": version
            })
        return json_objs

    def train(self, symbol: str, df, df_eval, version: str) -> DataFrame:
        print(f"#####Train {symbol}#######################")
        best = 0
        best_predictor = None
        result_df = DataFrame()

        if version == RsiBB().load(symbol).version:
            print(f"{symbol} Already trained with version {version}.")
            return result_df

        for training_set in self._BB_change_trainer(version):
            predictor = RsiBB()
            predictor.load(symbol)
            predictor.setup(training_set)
            res = predictor.step(df, df_eval, self._analytics)

            reward = res["reward"]
            avg_reward = res["success"]
            frequ = res["trade_frequency"]
            w_l = res["win_loss"]
            minutes = res["avg_minutes"]
            predictor.setup({"best_result": w_l})

            res = Series([symbol, reward, avg_reward, frequ, w_l, minutes],
                         index=["Symbol", "Reward", "Avg Reward", "Frequence", "WinLos", "Minutes"])
            res = res.append(predictor.get_config())
            result_df = result_df.append(res,
                                         ignore_index=True)

            if avg_reward > best and frequ > 0.005 and w_l > 0.66:
                best = avg_reward
                best_predictor = predictor
                print(f"{symbol} - {predictor.get_config()} - "
                      f"Avg Reward: {avg_reward:6.5} "
                      f"Avg Min {int(minutes)}  "
                      f"Freq: {frequ:4.3} "
                      f"WL: {w_l:3.2}")

        if best_predictor is not None:
            print(f"{symbol} Overwrite result.")
            best_predictor.save(symbol)
        else:
            print(f"{symbol} Couldnt find good result")
        return result_df
