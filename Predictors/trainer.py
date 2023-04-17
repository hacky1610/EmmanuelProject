import pandas as pd
from pandas import DataFrame,Series
import random
from Predictors import RsiStoch,CCI_EMA,RsiStochMacd

class Trainer:

    def __init__(self):
        pass


    def _read_data(self,symbol:str):
        try:
            df = pd.read_csv(f"./Data/{symbol}_1hour.csv", delimiter=",")
            df_eval = pd.read_csv(f"./Data/{symbol}_5min.csv", delimiter=",")
        except:
            return DataFrame(),DataFrame()
        df_eval.drop(columns=["level_0"], inplace=True)
        return df, df_eval

    def train_RSI_STOCH(self, symbol: str) -> DataFrame:
        print(f"#####Train {symbol}#######################")
        result_df = DataFrame()

        df, df_eval = self._read_data(symbol)
        if len(df) == 0 or len(df_eval) == 0:
            return result_df

        p1_list = list(range(2, 6))
        stop_list = [1.8,2.0, 2.3, 2.7, 3., 3.5]
        limit_list = [1.8,2.0, 2.3, 2.7, 3., 3.5]
        upper_limit_list = [75]  # list(range(75,85,5))
        lower_limit_list = [25]  # list(range(15,25,5))
        rsi_upper_limit_list = list(range(65, 85, 3))
        rsi_lower_limit_list = list(range(17, 35, 3))
        stoch_peek_list = [2, 3, 4]
        best = 0

        random.shuffle(p1_list)
        random.shuffle(stop_list)
        random.shuffle(limit_list)
        random.shuffle(upper_limit_list)
        random.shuffle(lower_limit_list)

        for ul in upper_limit_list:
            for ll   in lower_limit_list:
                for rul in rsi_upper_limit_list:
                    for rll in rsi_lower_limit_list:
                        predictor = RsiStoch({
                            "upper_limit": ul,
                            "lower_limit": ll,
                            "rsi_upper_limit": rul,
                            "rsi_lower_limit": rll,
                        })
                        res = predictor.step(df, df_eval)
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

                        if avg_reward > best and frequ > 0.008:
                            best = avg_reward
                            print(f"{symbol} - {predictor.get_config_as_string()} - "
                                  f"Avg Reward: {avg_reward:6.5} "
                                  f"Avg Min {int(minutes)}  "
                                  f"Freq: {frequ:4.3} "
                                  f"WL: {w_l:3.2}")
        return result_df

    def train_RSI_STOCH_MACD(self, symbol: str) -> DataFrame:
        print(f"#####Train {symbol}#######################")
        result_df = DataFrame()

        df, df_eval = self._read_data(symbol)
        if len(df) == 0 or len(df_eval) == 0:
            return result_df

        p1_list = list(range(2, 6))
        stop_list = [2.1, 2.5, 3., 3.5]
        limit_list = [2.1, 2.5, 3., 3.5]
        upper_limit_list = [75]  # list(range(75,85,5))
        lower_limit_list = [25]  # list(range(15,25,5))
        rsi_upper_limit_list = list(range(65, 85, 3))
        rsi_lower_limit_list = list(range(17, 35, 3))
        stoch_peek_list = [2, 3, 4]
        factor_list = [.8 ,.9,1.,1.3,1.7,2]
        best = 0

        random.shuffle(p1_list)
        random.shuffle(stop_list)
        random.shuffle(limit_list)
        random.shuffle(upper_limit_list)
        random.shuffle(lower_limit_list)

        for factor in factor_list:
            predictor = RsiStochMacd({
                "diff_factor": factor})
            res = predictor.step(df,df_eval)
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

            if avg_reward > best and frequ > 0.008:
                best = avg_reward
                print(f"{symbol} - {predictor.get_config_as_string()} - "
                      f"Avg Reward: {avg_reward:6.5} "
                      f"Avg Min {int(minutes)}  "
                      f"Freq: {frequ:4.3} "
                      f"WL: {w_l:3.2}")
        return result_df


    def train_CCI_EMA(self,symbol: str):
        print(f"#####Train {symbol}#######################")
        result_df = DataFrame()

        df, df_eval = self._read_data(symbol)
        if len(df) == 0 or len(df_eval) == 0:
            return result_df

        p1_list = list(range(2, 12, 3))
        p2_list = list(range(2, 12, 3))
        stop_list = [1.5, 1.8, 2.1, 2.5]
        limit_list = [1.5, 1.8, 2.1, 2.5, 3., 3.5]
        upper_limit_list = list(range(90, 95, 5))
        lower_limit_list = list(range(-110, -90, 5))
        best = 0

        random.shuffle(p1_list)
        random.shuffle(p2_list)
        random.shuffle(stop_list)
        random.shuffle(limit_list)
        random.shuffle(upper_limit_list)
        random.shuffle(lower_limit_list)

        for p1 in p1_list:
            for p2 in p2_list:
                for stop in stop_list:
                    for limit in limit_list:
                        for upper_limit in upper_limit_list:
                            for lower_limit in lower_limit_list:
                                predictor = CCI_EMA({
                                    "period_1": p1,
                                    "period_2": p2,
                                    "stop": stop,
                                    "limit": limit,
                                    "upper_limit": upper_limit,
                                    "lower_limit": lower_limit})
                                res = predictor.step(df,df_eval)
                                reward = res["reward"]
                                avg_reward = res["success"]
                                frequ = res["trade_frequency"]
                                w_l = res["win_loss"]
                                minutes = res["avg_minutes"]

                                if avg_reward > best:
                                    best = avg_reward
                                    print(f"{symbol} - {predictor.get_config()} - "
                                          f"Avg Reward: {avg_reward:6.5} "
                                          f"Avg Min {int(minutes)}  "
                                          f"Freq: {frequ:4.3} "
                                          f"WL: {w_l:3.2}")


