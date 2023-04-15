from pandas import DataFrame
import matplotlib.pyplot as plt
import pandas as pd

def evaluate(predictor,df_train:DataFrame, df_eval:DataFrame,print:bool=False):
    reward = 0
    losses = 0
    wins = 0

    if print:
        plt.figure(figsize=(15, 6))
        plt.cla()
        plt.plot(pd.to_datetime(df_eval["date"]), df_eval["close"], color='#d3d3d3', alpha=0.5,
                      label="Chart")

    trading_minutes = 0
    last_exit = df_train.date[0]
    for i in range(len(df_train)):
        if df_train.date[i] < last_exit:
            continue
        action = predictor.predict(df_train[:i + 1])
        if action == predictor.NONE:
            continue

        open_price = df_train.close[i]
        future = df_eval[df_eval["date"] > df_train.date[i]]
        future.reset_index(inplace=True)

        if action == predictor.BUY:
            if print:
                plt.plot(pd.to_datetime(df_train.date[i]), df_train.close[i], 'b^', label="Buy")
            for j in range(len(future)):
                trading_minutes += 5
                close = future.close[j]
                stop, limit = predictor.get_stop_limit()
                if close > open_price + limit:
                    # Won
                    if print:
                        plt.plot(pd.to_datetime(future.date[j]), future.close[j], 'go')
                    reward += limit
                    wins += 1
                    last_exit = future.date[j]
                    break
                elif close < open_price - stop:
                    # Loss
                    if print:
                        plt.plot(pd.to_datetime(future.date[j]), future.close[j], 'ro')
                    reward -= stop
                    losses += 1
                    last_exit = future.date[j]
                    break
        elif action == predictor.SELL:
            if print:
                plt.plot(pd.to_datetime(df_train.date[i]), df_train.close[i], 'bv', label="Sell")
            for j in range(len(future)):
                trading_minutes += 5
                close = future.close[j]
                stop, limit = predictor.get_stop_limit()
                if close < open_price - limit:
                    # Won
                    if print:
                        plt.plot(pd.to_datetime(future.date[j]), future.close[j], 'go')
                    reward += limit
                    wins += 1
                    last_exit = future.date[j]
                    break
                elif close > open_price + stop:
                    if print:
                        plt.plot(pd.to_datetime(future.date[j]), future.close[j], 'ro')
                    reward -= stop
                    losses += 1
                    last_exit = future.date[j]
                    break

    if print:
        plt.show()

    trades = wins + losses
    if trades == 0:
        return 0, 0, 0, 0, 0
    return reward, reward / trades, trades / len(df_train), wins / trades , trading_minutes / trades