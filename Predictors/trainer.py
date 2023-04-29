import pandas as pd
from pandas import DataFrame,Series
import random
from Predictors.rsi_stoch import RsiStoch
from Predictors.rsi_bb import RsiBB

class Trainer:

    def __init__(self,analytics):
        self._analytics = analytics

    def _read_data(self,symbol:str):
        try:
            df = pd.read_csv(f"./Data/{symbol}_1hour.csv", delimiter=",")
            df_eval = pd.read_csv(f"./Data/{symbol}_5min.csv", delimiter=",")
        except:
            return DataFrame(),DataFrame()
        df_eval.drop(columns=["level_0"], inplace=True)
        return df, df_eval

    def train_RSI_STOCH(self, symbol: str, df, df_eval) -> DataFrame:
        print(f"#####Train {symbol}#######################")
        if RsiStoch().saved(symbol):
            print("Already trained")
            return DataFrame()

        result_df = DataFrame()
        p1_list = [3] #list(range(2, 6))
        stop_list = [1.8,2.0, 2.3, 2.7, 3., 3.5]
        limit_list = [1.8,2.0, 2.3, 2.7, 3., 3.5]
        upper_limit_list = [78] #list(range(75,81,5))
        lower_limit_list = [20] #list(range(15,25,5))
        rsi_upper_limit_list = list(range(65, 80, 3))
        rsi_lower_limit_list = list(range(17, 30, 3))
        stoch_peek_list = [2, 3, 4]
        best = 0
        best_predictor = None

        random.shuffle(p1_list)
        random.shuffle(stop_list)
        random.shuffle(limit_list)
        random.shuffle(upper_limit_list)
        random.shuffle(lower_limit_list)

        for p in p1_list:
            for rul in rsi_upper_limit_list:
                for rll in rsi_lower_limit_list:
                    for ul in upper_limit_list:
                        for ll in lower_limit_list:
                            for st in stop_list:
                                for li in limit_list:
                                    predictor = RsiStoch({
                                        "period_1": p,
                                        "rsi_upper_limit": rul,
                                        "rsi_lower_limit": rll,
                                        "upper_limit": ul,
                                        "lower_limit": ll,
                                        "stop": st,
                                        "limit": li,
                                    })
                                    res = predictor.step(df, df_eval,self._analytics )
                                    reward = res["reward"]
                                    avg_reward = res["success"]
                                    frequ = res["trade_frequency"]
                                    w_l = res["win_loss"]
                                    minutes = res["avg_minutes"]

                                    res = Series([symbol, reward, avg_reward, frequ, w_l, minutes],
                                                 index=["Symbol", "Reward", "Avg Reward", "Frequence", "WinLos", "Minutes"])
                                    res = res.append(predictor.get_config())
                                    result_df = result_df.append(res,
                                                                 ignore_index=True)

                                    if avg_reward > best and frequ > 0.03 and w_l > 0.75:
                                        best = avg_reward
                                        best_predictor = predictor
                                        print(f"{symbol} - {predictor.get_config_as_string()} - "
                                              f"Avg Reward: {avg_reward:6.5} "
                                              f"Avg Min {int(minutes)}  "
                                              f"Freq: {frequ:4.3} "
                                              f"WL: {w_l:3.2}")

        if best_predictor is not None:
            best_predictor.save(symbol)
        else:
            print("Couldnt find good result")
        return result_df

    def train_RSI_BB(self, symbol: str, df, df_eval, version:str) -> DataFrame:
        print(f"#####Train {symbol}#######################")

        if version == RsiBB().load(symbol).version:
            return DataFrame()

        result_df = DataFrame()
        p1_list = list(range(2, 5))
        p2_list = list(range(2, 5))
        peak_count_list = list(range(0, 4))
        rsi_trend_list = [.005,.01,.03,.05]
        stop_list = [1.8,2.0, 2.3, 2.7, 3.]
        limit_list = [1.8,2.0, 2.3, 2.7, 3]
        rsi_upper_limit_list = list(range(65, 80, 3))
        rsi_lower_limit_list = list(range(20, 35, 3))
        best = 0
        best_predictor = None

        random.shuffle(p1_list)
        random.shuffle(stop_list)
        random.shuffle(limit_list)

        for ul in rsi_upper_limit_list:
            for ll in rsi_lower_limit_list:
                for trend in rsi_trend_list:
                    for p1 in p1_list:
                            predictor = RsiBB()
                            predictor.load(symbol)

                            predictor.setup({
                                "rsi_upper_limit": ul,
                                "rsi_lower_limit": ll,
                                "rsi_trend": trend,
                                "period_1": p1,
                                "period_2": 2,
                                "peak_count":0,
                                "stop": 2,
                                "limit": 2,
                                "version": version
                            })
                            res = predictor.step(df, df_eval,self._analytics )
                            reward = res["reward"]
                            avg_reward = res["success"]
                            frequ = res["trade_frequency"]
                            w_l = res["win_loss"]
                            minutes = res["avg_minutes"]
                            predictor.setup({"best_result":w_l})

                            res = Series([symbol, reward, avg_reward, frequ, w_l, minutes],
                                         index=["Symbol", "Reward", "Avg Reward", "Frequence", "WinLos", "Minutes"])
                            res = res.append(predictor.get_config())
                            result_df = result_df.append(res,
                                                         ignore_index=True)

                            if avg_reward > best and frequ > 0.005 and w_l > 0.6:
                                best = avg_reward
                                best_predictor = predictor

                                print(f"{symbol} - {predictor.get_config()} - "
                                      f"Avg Reward: {avg_reward:6.5} "
                                      f"Avg Min {int(minutes)}  "
                                      f"Freq: {frequ:4.3} "
                                      f"WL: {w_l:3.2}")

        if best_predictor is not None:
            best_predictor.save(symbol)
        else:
            print("Couldnt find good result")
        return result_df




