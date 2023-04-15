from Predictors import *
import pandas as pd
from Connectors.IG import IG
import random
from BL.utils import ConfigReader

def train_CCI_EMA(symbol:str):
    print(f"#####Train {symbol}#######################")
    df = pd.read_csv(f"./Data/{symbol}_1hour.csv", delimiter=",")
    df_eval = pd.read_csv(f"./Data/{symbol}_5min.csv", delimiter=",")
    df_eval.drop(columns=["level_0"], inplace=True)

    #print(evaluate(CCI_EMA({"df": df, "df_eval": df_eval}),df,df_eval))

    p1_list = list(range(2,12,3))
    p2_list = list(range(2,12,3))
    stop_list = [1.5,1.8,2.1,2.5]
    limit_list = [1.5,1.8,2.1,2.5,3.,3.5]
    upper_limit_list = list(range(90,95,5))
    lower_limit_list = list(range(-110,-90,5))
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
                                "period_1":p1,
                                "period_2":p2,
                                "df":df,
                                "df_eval":df_eval,
                                "stop":stop,
                                "limit":limit,
                                "upper_limit":upper_limit,
                                "lower_limit":lower_limit})
                            res = predictor.step()
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
                                      f"WL: {w_l:3.2}" )

def train_RSI_STOCK_MACHD(symbol:str):
    print(f"#####Train {symbol}#######################")
    try:
        df = pd.read_csv(f"./Data/{symbol}_1hour.csv", delimiter=",")
        df_eval = pd.read_csv(f"./Data/{symbol}_5min.csv", delimiter=",")
    except:
        return
    df_eval.drop(columns=["level_0"], inplace=True)

    #print(evaluate(CCI_EMA({"df": df, "df_eval": df_eval}),df,df_eval))

    p1_list = list(range(2,5))
    stop_list = [2.1,2.5,3.,3.5]
    limit_list = [2.1,2.5,3.,3.5]
    upper_limit_list = [75] #list(range(75,85,5))
    lower_limit_list = [25] #list(range(15,25,5))
    rsi_upper_limit_list = list(range(65,85,3))
    rsi_lower_limit_list = list(range(17,35,3))
    best = 0

    random.shuffle(p1_list)
    random.shuffle(stop_list)
    random.shuffle(limit_list)
    random.shuffle(upper_limit_list)
    random.shuffle(lower_limit_list)


    for p1 in p1_list:
            for stop in stop_list:
                for limit in limit_list:
                    for rsiu in rsi_upper_limit_list:
                        for rsil in rsi_lower_limit_list:
                            for upper_limit in upper_limit_list:
                                for lower_limit in lower_limit_list:
                                    predictor = RsiStoch({
                                        "period_1":p1,
                                        "df":df,
                                        "df_eval":df_eval,
                                        "rsi_upper_limit":rsiu,
                                        "rsi_lower_limit":rsil,
                                        "stop": stop,
                                        "limit": limit,
                                        "upper_limit":upper_limit,
                                        "lower_limit":lower_limit})
                                    res = predictor.step()
                                    reward = res["reward"]
                                    avg_reward = res["success"]
                                    frequ = res["trade_frequency"]
                                    w_l = res["win_loss"]
                                    minutes = res["avg_minutes"]

                                    if avg_reward > best and frequ > 0.008:
                                        best = avg_reward
                                        print(f"{symbol} - {predictor.get_config()} - "
                                              f"Avg Reward: {avg_reward:6.5} "
                                              f"Avg Min {int(minutes)}  "
                                              f"Freq: {frequ:4.3} "
                                              f"WL: {w_l:3.2}" )

markets = IG(conf_reader=ConfigReader()).get_markets(tradebale=False)

for m in markets:
    train_RSI_STOCK_MACHD(m["symbol"])

