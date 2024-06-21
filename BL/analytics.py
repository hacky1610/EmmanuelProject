import datetime

from tqdm import tqdm

from BL.eval_result import EvalResult, TradeResult
from Connectors.market_store import MarketStore
from Predictors.utils import TimeUtils
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer
from pandas import DataFrame
from BL.datatypes import TradeAction
import pandas as pd
from datetime import timedelta
from UI.base_viewer import BaseViewer


class Analytics:

    def __init__(self, market_store:MarketStore, tracer: Tracer = ConsoleTracer()):
        self._tracer = tracer
        self._market_store =  market_store

    @staticmethod
    def _create_additional_info(row, *args):
        text = ""
        for i in args:
            text += f"{i}:" + "{0:0.5}".format(row[i]) + "\r\n"

        return text

    def evaluate(self, predictor,
                 df: DataFrame,
                 df_eval: DataFrame,
                 symbol: str,
                 scaling: int,
                 viewer: BaseViewer = BaseViewer(),
                 only_one_position: bool = True,
                 filter=None) -> EvalResult:

        assert len(df) > 0
        assert len(df_eval) > 0

        reward = 0
        losses = 0
        wins = 0
        trading_minutes = 0
        spread = self._calc_spread(df)
        old_tracer = predictor._tracer
        predictor._tracer = Tracer()
        last_exit = df.date[0]

        viewer.init(f"Evaluation of  <a href='https://de.tradingview.com/chart/?symbol={symbol}'>{symbol}</a>",
                    df, df_eval)
        viewer.print_graph()

        trades = []

        market = self._market_store.get_market(symbol)

        if market is None:
            print(f"There is no market for {symbol}")
            return None


        for i in tqdm(range(len(df) - 1)):
            current_index = i + 1
            if filter is not None and TimeUtils.get_time_string(filter) != df.date[current_index]:
                continue

            open_price = df.open[current_index]

            if only_one_position and df.date[i] < last_exit:
                continue

            action = predictor.predict(df[:current_index])
            if action == TradeAction.NONE:
                continue

            stop = market.get_pip_value(predictor._stop, scaling)
            limit = market.get_pip_value(predictor._limit, scaling)

            trade:TradeResult = TradeResult()
            trade.action = action
            trade.last_df_time = df.date[current_index]
            trade.opening = df.close[current_index]
            trades.append(trade)

            future = df_eval[pd.to_datetime(df_eval["date"]) > pd.to_datetime(df.date[i]) + timedelta(hours=1)]
            future.reset_index(inplace=True, drop=True)

            additonal_text = self._create_additional_info(df.iloc[current_index],
                                                          "RSI", "CCI", "MACD", "SIGNAL", "PSAR")
            additonal_text += df.iloc[current_index].date

            if action == TradeAction.BUY:
                open_price = open_price + spread

                viewer.print_buy(df[i + 1:i + 2].index.item(), open_price, additonal_text)

                for j in range(len(future)):
                    trading_minutes += 5
                    high = future.high[j]
                    low = future.low[j]
                    train_index = df[df.date <= future.date[j]][-1:].index.item()

                    if high > open_price + limit:
                        # Won
                        viewer.print_won(train_index, future.close[j])
                        reward += limit
                        wins += 1
                        last_exit = future.date[j]
                        trade.result = "won"
                        trade.profit = limit
                        trade.close_df_time = last_exit
                        trade.closing = high
                        break
                    elif low < open_price - stop:
                        # Loss
                        viewer.print_lost(train_index, future.close[j])
                        reward -= stop
                        losses += 1
                        last_exit = future.date[j]
                        trade.result = "lost"
                        trade.profit = stop * -1
                        trade.closing = low
                        trade.close_df_time = last_exit
                        break
            elif action == TradeAction.SELL:
                open_price = open_price - spread

                viewer.print_sell(df[i + 1:i + 2].index.item(), open_price, additonal_text)

                for j in range(len(future)):
                    trading_minutes += 5
                    high = future.high[j]
                    low = future.low[j]
                    train_index = df[df.date <= future.date[j]][-1:].index.item()

                    if low < open_price - limit:
                        # Won
                        viewer.print_won(train_index, future.close[j])
                        reward += limit
                        wins += 1
                        last_exit = future.date[j]
                        trade.result = "won"
                        trade.profit = limit
                        trade.closing = high
                        trade.close_df_time = last_exit
                        break
                    elif high > open_price + stop:
                        viewer.print_lost(train_index, future.close[j])
                        reward -= stop
                        losses += 1
                        trade.result = "lost"
                        trade.profit = stop * -1
                        last_exit = future.date[j]
                        trade.closing = low
                        trade.close_df_time = last_exit
                        break

        predictor._tracer = old_tracer
        reward_eur = reward * scaling / market.pip_euro
        ev_res = EvalResult(trades, reward_eur, wins + losses, len(df), trading_minutes, wins, scan_time=datetime.datetime.now())
        viewer.update_title(f"{ev_res}")
        viewer.show()

        return ev_res

    @staticmethod
    def _calc_spread(df_train):
        return (abs((df_train.close - df_train.close.shift(1))).median()) * 0.8
