from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer
from pandas import DataFrame
import pandas as pd
from datetime import timedelta
from UI.base_viewer import BaseViewer


class Analytics:

    def __init__(self, tracer: Tracer = ConsoleTracer()):
        self._tracer = tracer

    def evaluate(self, predictor,
                 df_train: DataFrame,
                 df_eval: DataFrame,
                 symbol: str = "",
                 viewer: BaseViewer = BaseViewer(),
                 only_one_position: bool = True):

        assert len(df_train) > 0
        assert len(df_eval) > 0

        reward = 0
        losses = 0
        wins = 0
        spread = (abs((df_train.close - df_train.close.shift(1))).median()) * 0.8
        old_tracer = predictor._tracer
        predictor._tracer = Tracer()
        viewer.init(f"Evaluation of  <a href='https://de.tradingview.com/chart/?symbol={symbol}'>{symbol}</a>",
                    df_train, df_eval)
        viewer.print_graph()
        #s = PivotScanner(viewer=viewer)
        #s.scan_points(df_train)


        trading_minutes = 0
        last_exit = df_train.date[0]
        for i in range(len(df_train) - 1):

            # df_train.date[i] == '2023-05-04T02:00:00.000Z'
            open_price = df_train.open[i + 1]

            if only_one_position and df_train.date[i] < last_exit:
                continue

            action, limit, stop = predictor.predict(df_train[:i + 1])
            if action == predictor.NONE:
                continue

            future = df_eval[pd.to_datetime(df_eval["date"]) > pd.to_datetime(df_train.date[i]) + timedelta(hours=1)]
            future.reset_index(inplace=True)

            additonal_text = f"{df_train.RSI[i+1]}"

            if action == predictor.BUY:
                open_price = open_price + spread

                viewer.print_buy(df_train[i+1:i+2].index.item(), open_price,additonal_text )

                for j in range(len(future)):
                    trading_minutes += 5
                    high = future.high[j]
                    low = future.low[j]
                    train_index = df_train[df_train.date <= future.date[j]][-1:].index.item()

                    if high > open_price + limit:
                        # Won
                        viewer.print_won(train_index, future.close[j])
                        reward += limit
                        wins += 1
                        last_exit = future.date[j]
                        break
                    elif low < open_price - stop:
                        # Loss
                        viewer.print_lost(train_index, future.close[j])
                        reward -= stop
                        losses += 1
                        last_exit = future.date[j]
                        break
            elif action == predictor.SELL:
                open_price = open_price - spread

                viewer.print_sell(df_train[i+1:i+2].index.item(), open_price, additonal_text)

                for j in range(len(future)):
                    trading_minutes += 5
                    high = future.high[j]
                    low = future.low[j]
                    train_index = df_train[df_train.date <= future.date[j]][-1:].index.item()

                    if low < open_price - limit:
                        # Won
                        viewer.print_won(train_index, future.close[j])
                        reward += limit
                        wins += 1
                        last_exit = future.date[j]
                        break
                    elif high > open_price + stop:
                        viewer.print_lost(train_index, future.close[j])
                        reward -= stop
                        losses += 1
                        last_exit = future.date[j]
                        break


        trades = wins + losses
        predictor._tracer = old_tracer
        if trades == 0:
            viewer.show()
            return 0, 0, 0, 0, 0, 0

        viewer.update_title(f"Result {round(wins / trades,7)}")
        viewer.show()

        return reward, \
            round(reward / trades,7), \
            round(trades / len(df_train),7), \
            round(wins / trades,7), \
            round(trading_minutes / trades,7), \
            trades
