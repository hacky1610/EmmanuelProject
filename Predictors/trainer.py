from pandas import DataFrame, Series
import random
import itertools
from Predictors.sup_res_candle import SupResCandle


class Trainer:

    def __init__(self, analytics):
        self._analytics = analytics



    def is_trained(self,symbol:str,version:str):
        saved_predictor = SupResCandle().load(symbol)
        return  version == saved_predictor.version

    def train(self, symbol: str, df, df_eval, version: str) -> DataFrame:
        print(f"#####Train {symbol}#######################")
        best = 0
        best_predictor = None
        result_df = DataFrame()

        sets = SupResCandle.get_training_sets(version)
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
