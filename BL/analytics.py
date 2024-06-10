import datetime
from typing import List

from tqdm import tqdm

from tqdm import tqdm

from BL.eval_result import EvalResult, TradeResult
from Connectors.market_store import MarketStore
from Predictors.utils import TimeUtils
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer
from pandas import DataFrame, Series
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

            if action == TradeAction.BOTH:
                trades.append(TradeResult(action, 0, i))
                continue

            stop = market.get_pip_value(predictor._stop, scaling)
            limit = market.get_pip_value(predictor._limit, scaling)

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
                        trades.append(TradeResult(action,limit,i))

                        break
                    elif low < open_price - stop:
                        # Loss
                        viewer.print_lost(train_index, future.close[j])
                        reward -= stop
                        losses += 1
                        last_exit = future.date[j]
                        trades.append(TradeResult(action, stop * -1, i))

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
                        trades.append(TradeResult(action, limit , i))
                        break
                    elif high > open_price + stop:
                        viewer.print_lost(train_index, future.close[j])
                        reward -= stop
                        losses += 1
                        last_exit = future.date[j]
                        trades.append(TradeResult(action, stop * -1, i))
                        break

        predictor._tracer = old_tracer
        reward_eur = reward * scaling / market.pip_euro
        ev_res = EvalResult(trades, reward_eur, wins + losses,
                            len(df), trading_minutes, wins,
                            scan_time=datetime.datetime.now(), symbol=symbol, indicator=predictor._indicator_names[0])
        viewer.update_title(f"{ev_res}")
        viewer.show()

        return ev_res

    def get_signals(self, predictor,
                 df: DataFrame) -> DataFrame:

        assert len(df) > 0

        trades = DataFrame()

        for i in range(len(df) - 1):
            current_index = i + 1
            action = predictor.predict(df[:current_index])

            if action != TradeAction.NONE:
                trades = trades.append(Series(index=["action","chart_index"], data=[action, i]), ignore_index=True)

        return trades

    def simulate(self,
                 action:str,
                 stop_euro:float,
                 limit_euro:float,
                 df: DataFrame,
                 df_eval: DataFrame,
                 symbol: str,
                 scaling: int) -> EvalResult:

        assert len(df) > 0
        assert len(df_eval) > 0

        def get_next_index(df_:DataFrame, last_exit_time) -> int:
            filtered_df = df_[df_.date > last_exit_time]
            if len(filtered_df) > 0:
                return filtered_df[: 1].index.item()
            return -1

        trading_minutes = 0
        spread = self._calc_spread(df)
        market = self._market_store.get_market(symbol)
        simulation_result = DataFrame()

        if market is None:
            print(f"There is no market for {symbol}")
            return None

        stop = market.get_pip_value(stop_euro, scaling)
        limit = market.get_pip_value(limit_euro, scaling)

        for i in tqdm(range(len(df) - 1)):
            current_index = i + 1
            open_price = df.open[current_index]
            future = df_eval[pd.to_datetime(df_eval["date"]) > pd.to_datetime(df.date[i]) + timedelta(hours=1)]
            future.reset_index(inplace=True, drop=True)

            if action == TradeAction.BUY:
                open_price = open_price + spread

                for j in range(len(future)):
                    trading_minutes += 5
                    high = future.high[j]
                    low = future.low[j]

                    if high > open_price + limit:
                        # Won
                        last_exit = future.date[j]
                        simulation_result = simulation_result.append(Series(index=["action","result","chart_index", "next_index"],
                                                                            data=[action,limit,i, get_next_index(df,last_exit)]), ignore_index=True)
                        break
                    elif low < open_price - stop:
                        # Loss
                        last_exit = future.date[j]
                        simulation_result = simulation_result.append(
                            Series(index=["action", "result", "chart_index", "next_index"],
                                   data=[action, stop * -1, i,get_next_index(df,last_exit)]),
                            ignore_index=True)
                        break
            elif action == TradeAction.SELL:
                open_price = open_price - spread
                for j in range(len(future)):
                    trading_minutes += 5
                    high = future.high[j]
                    low = future.low[j]

                    if low < open_price - limit:
                        # Won
                        last_exit = future.date[j]
                        simulation_result = simulation_result.append(
                            Series(index=["action", "result", "chart_index", "next_index"], data=[action, limit, i, get_next_index(df,last_exit)]),
                            ignore_index=True)
                        break
                    elif high > open_price + stop:
                        last_exit = future.date[j]
                        simulation_result = simulation_result.append(
                            Series(index=["action", "result", "chart_index", "next_index"], data=[action, stop * -1, i, get_next_index(df,last_exit)]),
                            ignore_index=True)
                        break

        return simulation_result

    def foo(self, signals:DataFrame, df_buy_results: DataFrame, df_sell_results: DataFrame):

        overall_result = 0
        next_index = 0
        for i in range(len(signals)):
            signal = signals.iloc[i]
            if signal["index"] > next_index:
                if signal.action == TradeAction.BUY:
                    res = df_buy_results[df_buy_results.chart_index == signal["index"]]
                if signal.action == TradeAction.SELL:
                    res = df_sell_results[df_sell_results.chart_index == signal["index"]]
                if len(res) == 1:
                    overall_result = overall_result + res[:1].result.item()
                    next_index = res[:1].next_index.item()

        return overall_result










    @staticmethod
    def _calc_spread(df_train):
        return (abs((df_train.close - df_train.close.shift(1))).median()) * 0.8
