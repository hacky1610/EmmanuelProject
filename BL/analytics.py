from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer
from pandas import DataFrame
import pandas as pd
from datetime import timedelta
from UI.base_viewer import BaseViewer


class Analytics:

    def __init__(self, tracer: Tracer = ConsoleTracer()):
        self._tracer = tracer

    def evaluate(self, predictor, train_data: DataFrame, eval_data: DataFrame, viewer: BaseViewer = BaseViewer()):
        reward = 0
        losses = 0
        wins = 0
        spread = (abs((train_data.close - train_data.close.shift(1))).median()) * 0.8
        old_tracer = predictor._tracer
        predictor._tracer = Tracer()

        viewer.init(train_data, eval_data)
        viewer.print_graph()

        trading_minutes = 0
        last_exit = train_data.date[0]

        def process_trade(action, open_price):
            nonlocal reward, losses, wins, trading_minutes, last_exit
            open_price += spread if action == predictor.BUY else -spread
            for j in range(len(eval_data)):
                trading_minutes += 5
                high = eval_data.high[j]
                low = eval_data.low[j]
                stop, limit = predictor.get_stop_limit(train_data[:i + 1])
                if (action == predictor.BUY and high > open_price + limit) or \
                    (action == predictor.SELL and low < open_price - limit):
                    viewer.print_won(eval_data.date[j], eval_data.close[j])
                    reward += limit
                    wins += 1
                    last_exit = eval_data.date[j]
                    return True
                elif (action == predictor.BUY and low < open_price - stop) or \
                        (action == predictor.SELL and high > open_price + stop):
                    viewer.print_lost(eval_data.date[j], eval_data.close[j])
                    reward -= stop
                    losses += 1
                    last_exit = eval_data.date[j]
                    return True
            return False

        for i in range(len(train_data)):
            if train_data.date[i] < last_exit:
                continue
            action = predictor.predict(train_data[:i + 1])
            if action == predictor.NONE:
                continue

            if action == predictor.BUY:
                viewer.print_buy(train_data.date[i], train_data.close[i])
            elif action == predictor.SELL:
                viewer.print_sell(train_data.date[i], train_data.close[i])

            if process_trade(action, train_data.close[i]):
                break

        viewer.show()

        trades = wins + losses
        predictor._tracer = old_tracer
        if trades == 0:
            return 0, 0, 0, 0, 0
        return reward, reward / trades, trades / len(train_data), wins / trades, trading_minutes / trades

