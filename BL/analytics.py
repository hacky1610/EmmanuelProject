from BL.candle import MultiCandle, MultiCandleType
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer
from pandas import DataFrame
import pandas as pd
from datetime import timedelta
from UI.base_viewer import BaseViewer


class Analytics:

    def __init__(self, tracer: Tracer = ConsoleTracer()):
        self._tracer = tracer

    def evaluate(self, predictor, df_train: DataFrame, df_eval: DataFrame, symbol:str = "", viewer: BaseViewer = BaseViewer()):
        reward = 0
        losses = 0
        wins = 0
        spread = (abs((df_train.close - df_train.close.shift(1))).median()) * 0.8
        old_tracer = predictor._tracer
        predictor._tracer = Tracer()

        viewer.init(f"Evaluation of {symbol}",df_train,df_eval)
        viewer.print_graph()

        trading_minutes = 0
        last_exit = df_train.date[0]
        for i in range(len(df_train) - 1):
            #df_train.date[i] == '2023-05-04T02:00:00.000Z'
            open_price = df_train.open[i + 1]

            #if i % 10 != 0:
            #    continue

            #if i > 3:
            #    c = MultiCandle(df_train[:i])
            #    t = c.get_type()
            #   if t != MultiCandleType.Unknown:
            #        viewer.print_text(df_train.date[i - 1], open_price, t)

            if df_train.date[i] < last_exit:
                continue
            action = predictor.predict(df_train[:i + 1])
            if action == predictor.NONE:
                continue

            future = df_eval[pd.to_datetime(df_eval["date"]) > pd.to_datetime(df_train.date[i]) + timedelta(hours=1)]
            future.reset_index(inplace=True)



            if action == predictor.BUY:
                open_price = open_price + spread

                viewer.print_buy(df_train.date[i + 1], open_price)


                for j in range(len(future)):
                    trading_minutes += 5
                    high = future.high[j]
                    low = future.low[j]
                    stop, limit = predictor.get_stop_limit(df_train[:i + 1])
                    if high > open_price + limit:
                        # Won
                        viewer.print_won(future.date[j], future.close[j])
                        reward += limit
                        wins += 1
                        last_exit = future.date[j]
                        break
                    elif low < open_price - stop:
                        # Loss
                        viewer.print_lost(future.date[j], future.close[j])
                        reward -= stop
                        losses += 1
                        last_exit = future.date[j]
                        break
            elif action == predictor.SELL:
                open_price = open_price - spread

                viewer.print_sell(df_train.date[i + 1], open_price)

                for j in range(len(future)):
                    trading_minutes += 5
                    high = future.high[j]
                    low = future.low[j]
                    stop, limit = predictor.get_stop_limit(df_train[:i + 1])
                    if low < open_price - limit:
                        # Won
                        viewer.print_won(future.date[j], future.close[j])

                        reward += limit
                        wins += 1
                        last_exit = future.date[j]
                        break
                    elif high > open_price + stop:
                        viewer.print_lost(future.date[j], future.close[j])
                        reward -= stop
                        losses += 1
                        last_exit = future.date[j]
                        break

        viewer.show()

        trades = wins + losses
        predictor._tracer = old_tracer
        if trades == 0:
            return 0, 0, 0, 0, 0, 0
        return reward, \
            reward / trades, \
            trades / len(df_train), \
            wins / trades, \
            trading_minutes / trades, \
            trades

