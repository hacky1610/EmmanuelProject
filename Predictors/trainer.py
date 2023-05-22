import pandas as pd
from pandas import DataFrame, Series
import random
from Predictors.rsi_stoch import RsiStoch

import itertools

from Predictors.sup_res_candle import SupResCandle


class Trainer:

    def __init__(self, analytics):
        self._analytics = analytics

    def _rsi_trainer(self, version: str):

        json_objs = []
        for rsi_upper, rsi_lower, trend in itertools.product(list(range(55, 80, 3)), list(range(20, 45, 3)),
                                                             [None, .005, .01, .03, .05]):
            json_objs.append({
                "rsi_upper_limit": rsi_upper,
                "rsi_lowe_limit": rsi_lower,
                "rsi_trend": trend,
                "version": version
            })
        return json_objs

    def _sr_trainer(self, version: str):

        json_objs = []
        for zig_zag_percent, merge_percent, min_bars_between_peaks in itertools.product([0.05, 0.1, 0.3, .7, .9], [0.05, 0.1, .03], [13,17,23]):
            json_objs.append({
                "zig_zag_percent": zig_zag_percent,
                "merge_percent": merge_percent,
                "min_bars_between_peaks": min_bars_between_peaks,
                "version": version
            })
        return json_objs

    def _sr_trainer2(self, version: str):

        json_objs = []
        for look_back_days, level_section_size in itertools.product([13,17,21],[0.7,1.0,1.3,1.7]):
            json_objs.append({
                "look_back_days": look_back_days,
                "level_section_size": level_section_size,
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
        for change in [None, 0.1, 0.3, .5, .7, 1.0]:
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
        saved_predictor = SupResCandle().load(symbol)

        if version == saved_predictor.version:
            print(f"{symbol} Already trained with version {version}.")
            return result_df

        sets = self._sr_trainer(version)
        random.shuffle(sets)
        for training_set in sets:
            predictor = SupResCandle()
            predictor.load(symbol)
            predictor.setup(training_set)
            res = predictor.step(df, df_eval, self._analytics)

            reward = res["reward"]
            avg_reward = res["success"]
            frequ = res["trade_frequency"]
            w_l = res["win_loss"]
            minutes = res["avg_minutes"]
            trades = res["trades"]
            predictor.setup({"best_result": w_l,
                             "best_reward": reward,
                             "frequence": frequ,
                             "trades": trades })

            res = Series([symbol, reward, avg_reward, frequ, w_l, minutes],
                         index=["Symbol", "Reward", "Avg Reward", "Frequence", "WinLos", "Minutes"])
            res = res.append(predictor.get_config())
            result_df = result_df.append(res,
                                         ignore_index=True)

            if reward > best and w_l > 0.66 and trades >= 5:
                best = reward
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
