from pandas import DataFrame
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer  import ConsoleTracer
from pandas import DataFrame
import matplotlib.pyplot as plt
import pandas as pd


class Analytics:

    def __init__(self,tracer:Tracer=ConsoleTracer()):
        self._tracer = tracer
    def has_peak(self, df:DataFrame, lockback:int = 3, max_limit:float=2.5):
        mean_diff = (df["high"] - df["low"]).mean()

        max = (df[lockback * -1:]["high"] - df[lockback * -1:]["low"]).max()

        if max > mean_diff * max_limit:
            self._tracer.debug(f"Peak of {max} compared to mean {mean_diff}. Limit times {max_limit} im the last {lockback} dates")
            return True

        return False

    def is_sleeping(self, df: DataFrame, lockback: int = 2, max_limit: float = 0.6):
        mean_diff = (df["high"] - df["low"]).mean()
        m = (df[lockback * -1:]["high"] - df[lockback * -1:]["low"]).mean()

        if m < mean_diff * max_limit:
            #
            self._tracer.debug(f"No movement {m} in the last {lockback} dates")
            return True

        return False

    def evaluate(self, predictor, df_train: DataFrame, df_eval: DataFrame, print_graph: bool = False):
        reward = 0
        losses = 0
        wins = 0
        spread = (abs((df_train.close - df_train.close.shift(1))).median()) * 0.8

        if print_graph:
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
                open_price = open_price + spread

                if print_graph:
                    plt.plot(pd.to_datetime(df_train.date[i]), df_train.close[i], 'b^', label="Buy")
                for j in range(len(future)):
                    trading_minutes += 5
                    high = future.high[j]
                    low = future.low[j]
                    stop, limit = predictor.get_stop_limit(df_train[:i + 1])
                    if high > open_price + limit:
                        # Won
                        if print_graph:
                            plt.plot(pd.to_datetime(future.date[j]), future.close[j], 'go')
                        reward += limit
                        wins += 1
                        last_exit = future.date[j]
                        break
                    elif low < open_price - stop:
                        # Loss
                        if print_graph:
                            plt.plot(pd.to_datetime(future.date[j]), future.close[j], 'ro')
                        reward -= stop
                        losses += 1
                        last_exit = future.date[j]
                        break
            elif action == predictor.SELL:
                open_price = open_price - spread

                if print_graph:
                    plt.plot(pd.to_datetime(df_train.date[i]), df_train.close[i], 'bv', label="Sell")
                for j in range(len(future)):
                    trading_minutes += 5
                    high = future.high[j]
                    low = future.low[j]
                    stop, limit = predictor.get_stop_limit(df_train[:i + 1])
                    if low < open_price - limit:
                        # Won
                        if print_graph:
                            plt.plot(pd.to_datetime(future.date[j]), future.close[j], 'go')
                        reward += limit
                        wins += 1
                        last_exit = future.date[j]
                        break
                    elif high > open_price + stop:
                        if print_graph:
                            plt.plot(pd.to_datetime(future.date[j]), future.close[j], 'ro')
                        reward -= stop
                        losses += 1
                        last_exit = future.date[j]
                        break

        if print_graph:
            plt.show()

        trades = wins + losses
        if trades == 0:
            return 0, 0, 0, 0, 0
        return reward, reward / trades, trades / len(df_train), wins / trades, trading_minutes / trades
