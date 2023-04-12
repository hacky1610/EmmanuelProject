from pandas import DataFrame
import matplotlib.pyplot as plt
import pandas as pd

def evaluate(predictor,df_train:DataFrame, df_eval:DataFrame):
    reward = 0
    losses = 0
    wins = 0

    #plt.figure(figsize=(15, 6))
    #plt.cla()
    #plt.plot(pd.to_datetime(df_train["date"]), df_train["close"], color='#d3d3d3', alpha=0.5,
                     # label="Chart")

    trading_minutes = 0
    for i in range(len(df_train)):
        action = predictor.predict(df_train[:i + 1])
        if action == predictor.NONE:
            continue

        open_price = df_train.close[i]
        future = df_eval[df_eval["date"] > df_train.date[i]]
        future.reset_index(inplace=True)

        if action == predictor.BUY:
            plt.plot(pd.to_datetime(df_train.date[i]), df_train.close[i], 'b^', label="Buy")
            for j in range(len(future)):
                trading_minutes += 5
                close = future.close[j]
                stop, limit = predictor.get_stop_limit()
                if close > open_price + limit:
                    # Won
                    #plt.plot(pd.to_datetime(future.date[j]), future.close[j], 'go')
                    reward += limit
                    wins += 1
                    break
                elif close < open_price - stop:
                    # Loss
                    #plt.plot(pd.to_datetime(future.date[j]), future.close[j], 'ro')
                    reward -= stop
                    losses += 1
                    break
        elif action == predictor.SELL:
            plt.plot(pd.to_datetime(df_train.date[i]), df_train.close[i], 'bv', label="Sell")
            for j in range(len(future)):
                trading_minutes += 5
                close = future.close[j]
                stop, limit = predictor.get_stop_limit()
                if close < open_price - limit:
                    # Won
                    #plt.plot(pd.to_datetime(future.date[j]), future.close[j], 'go')
                    reward += limit
                    wins += 1
                    break
                elif close > open_price + stop:
                    #plt.plot(pd.to_datetime(future.date[j]), future.close[j], 'ro')
                    reward -= stop
                    losses += 1
                    break

    #plt.show()

    trades = wins + losses
    if trades == 0:
        return 0, 0, 0, 0
    return reward, reward / trades, trades / len(df_train), wins / trades , trading_minutes / trades