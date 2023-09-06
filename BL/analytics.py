from BL.eval_result import EvalResult
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer
from pandas import DataFrame
import pandas as pd
from datetime import timedelta
from UI.base_viewer import BaseViewer


class Analytics:

    def __init__(self, tracer: Tracer = ConsoleTracer()):
        self._tracer = tracer

    @staticmethod
    def _create_additional_info(row, *args):
        text = ""
        for i in args:
            text += f"{i}:" + "{0:0.5}".format(row[i].item()) + "\r\n"

        return text

    def evaluate(self, predictor,
                 df_train: DataFrame,
                 df_eval: DataFrame,
                 symbol: str = "",
                 viewer: BaseViewer = BaseViewer(),
                 only_one_position: bool = True,
                 filter=None) -> EvalResult:

        assert len(df_train) > 0
        assert len(df_eval) > 0

        reward = 0
        losses = 0
        wins = 0
        trading_minutes = 0
        spread = self._calc_spread(df_train)
        old_tracer = predictor._tracer
        predictor._tracer = Tracer()
        last_exit = df_train.date[0]

        viewer.init(f"Evaluation of  <a href='https://de.tradingview.com/chart/?symbol={symbol}'>{symbol}</a>",
                    df_train, df_eval)
        viewer.print_graph()

        for i in range(len(df_train) - 1):
            current_index = i + 1
            if filter is not None and filter.strftime("%Y-%m-%dT%H:00:00.000Z") != df_train.date[current_index]:
                continue

            open_price = df_train.open[current_index]

            if only_one_position and df_train.date[i] < last_exit:
                continue

            action, stop, limit = predictor.predict(df_train[:current_index])
            if action == predictor.NONE:
                continue

            future = df_eval[pd.to_datetime(df_eval["date"]) > pd.to_datetime(df_train.date[i]) + timedelta(hours=1)]
            future.reset_index(inplace=True)

            additonal_text = self._create_additional_info(df_train.iloc[current_index], "RSI")

            if action == predictor.BUY:
                open_price = open_price + spread

                viewer.print_buy(df_train[i + 1:i + 2].index.item(), open_price, additonal_text)

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

                viewer.print_sell(df_train[i + 1:i + 2].index.item(), open_price, additonal_text)

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

        predictor._tracer = old_tracer
        ev_res = EvalResult(reward, wins + losses, len(df_train), trading_minutes, wins)
        viewer.update_title(f"{ev_res}")
        viewer.show()

        return ev_res

    @staticmethod
    def _calc_spread(df_train):
        return (abs((df_train.close - df_train.close.shift(1))).median()) * 0.8
