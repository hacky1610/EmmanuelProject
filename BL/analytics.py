import datetime
import sys
from collections import namedtuple

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

    def __init__(self, market_store: MarketStore, ig, tracer: Tracer = ConsoleTracer()):
        self._tracer = tracer
        self._market_store = market_store
        self._ig = ig

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
                 only_one_position: bool = True,
                 time_filter=None) -> EvalResult:

        assert len(df) > 0
        assert len(df_eval) > 0

        trading_minutes = 0
        spread = self._calc_spread(df)
        old_tracer = predictor._tracer
        predictor._tracer = Tracer()
        last_exit = df.date[0]
        trades = []
        market = self._market_store.get_market(symbol)

        if market is None:
            print(f"There is no market for {symbol}")
            return None

        distance = self._ig.get_stop_distance(market, "", scaling, check_min=False,
                                              intelligent_stop_distance=predictor.get_isl_distance())
        stop_pip = market.get_pip_value(predictor.get_stop(), scaling)
        limit_pip = market.get_pip_value(predictor.get_limit(), scaling)
        isl_entry_pip = market.get_pip_value(predictor.get_isl_entry(), scaling)

        for i in tqdm(range(len(df) - 1)):
            current_index = i + 1
            if time_filter is not None and TimeUtils.get_time_string(time_filter) != df.date[current_index]:
                continue

            if only_one_position and df.date[i] < last_exit:
                continue

            action = predictor.predict(df[:current_index])
            if action == TradeAction.NONE:
                continue

            if action == TradeAction.BOTH:
                trades.append(TradeResult(action, 0, i))
                continue

            open_price = df.close[current_index - 1]
            trade = TradeResult(action=action, open_time=df.date[current_index], opening=open_price)
            trades.append(trade)

            future = df_eval[pd.to_datetime(df_eval["date"]) > pd.to_datetime(df.date[i]) + timedelta(hours=1)]
            future.reset_index(inplace=True, drop=True)

            if action == TradeAction.BUY:
                open_price = open_price + spread
                if predictor._isl_open_end:
                    limit_price = sys.float_info.max
                else:
                    limit_price = open_price + limit_pip
                stop_price = open_price - stop_pip

                for j in range(len(future)):
                    trading_minutes += 5
                    high = future.high[j]
                    low = future.low[j]
                    close = future.close[j]

                    if high > limit_price:
                        # Won
                        last_exit = future.date[j]
                        trade.set_result(profit=market.get_euro_value(limit_price - open_price, scaling), closing=high,
                                         close_time=last_exit)
                        break
                    elif low < stop_price:
                        # Loss
                        last_exit = future.date[j]
                        trade.set_result(profit=market.get_euro_value(stop_price - open_price, scaling), closing=low,
                                         close_time=last_exit)
                        break

                    if predictor._use_isl:
                        if self._ig.is_ready_to_set_intelligent_stop(high - open_price, isl_entry_pip):
                            new_stop_level = close - distance
                            if new_stop_level > stop_price:
                                stop_price = new_stop_level
                                trade.set_intelligent_stop_used()


            elif action == TradeAction.SELL:
                open_price = open_price - spread
                if predictor._isl_open_end:
                    limit_price = sys.float_info.min
                else:
                    limit_price = open_price - limit_pip
                stop_price = open_price + stop_pip

                for j in range(len(future)):
                    trading_minutes += 5
                    high = future.high[j]
                    low = future.low[j]
                    close = future.close[j]

                    if low < limit_price:
                        # Won
                        last_exit = future.date[j]
                        trade.set_result(profit=market.get_euro_value(open_price - limit_price, scaling), closing=low,
                                         close_time=last_exit)
                        break
                    elif high > stop_price:
                        last_exit = future.date[j]
                        trade.set_result(profit=market.get_euro_value(open_price - stop_price, scaling), closing=high,
                                         close_time=last_exit)
                        break

                    if predictor._use_isl:
                        if self._ig.is_ready_to_set_intelligent_stop(open_price - low, isl_entry_pip):
                            new_stop_level = close + distance
                            if new_stop_level < stop_price:
                                stop_price = new_stop_level
                                trade.set_intelligent_stop_used()

        predictor._tracer = old_tracer
        ev_res = EvalResult(symbol=symbol, trades_results=trades, len_df=len(df), trade_minutes=trading_minutes,
                            scan_time=datetime.datetime.now())

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
                 isl_entry: float,
                 isl_distance: float,
                 use_isl: bool,
                 isl_open_end: bool,
                 df: DataFrame,
                 df_eval: DataFrame,
                 symbol: str,
                 scaling: int) -> DataFrame:

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

        print(f"Start simulation for {symbol}")

        stop_pip = market.get_pip_value(stop_euro, scaling)
        limit_pip = market.get_pip_value(limit_euro, scaling)
        isl_entry_pip = market.get_pip_value(isl_entry, scaling)
        distance = self._ig.get_stop_distance(market, "", scaling, check_min=False,
                                              intelligent_stop_distance=isl_distance)

        for i in tqdm(range(len(df) - 1)):
            current_index = i + 1
            open_price = df.close[current_index - 1]
            future = df_eval[pd.to_datetime(df_eval["date"]) > pd.to_datetime(df.date[i]) + timedelta(hours=1)]
            future.reset_index(inplace=True, drop=True)

            if action == TradeAction.BUY:
                open_price = open_price + spread
                if isl_open_end:
                    limit_price = sys.float_info.max
                else:
                    limit_price = open_price + limit_pip
                stop_price = open_price - stop_pip

                for j in range(len(future)):
                    trading_minutes += 5
                    high = future.high[j]
                    low = future.low[j]
                    close = future.close[j]

                    if high > limit_price:
                        # Won
                        last_exit = future.date[j]
                        simulation_result = simulation_result.append(Series(index=["action","result","chart_index", "next_index"],
                                                                            data=[action,limit_price - open_price,i, get_next_index(df,last_exit)]), ignore_index=True)
                        break
                    elif low < stop_price:
                        # Loss
                        last_exit = future.date[j]
                        simulation_result = simulation_result.append(
                            Series(index=["action", "result", "chart_index", "next_index"],
                                   data=[action, stop_price - open_price, i,get_next_index(df,last_exit)]),
                            ignore_index=True)
                        break

                    if use_isl:
                        if self._ig.is_ready_to_set_intelligent_stop(high - open_price, isl_entry_pip):
                            new_stop_level = close - distance
                            if new_stop_level > stop_price:
                                stop_price = new_stop_level

            elif action == TradeAction.SELL:
                open_price = open_price - spread
                if isl_open_end:
                    limit_price = sys.float_info.min
                else:
                    limit_price = open_price - limit_pip
                stop_price = open_price + stop_pip
                for j in range(len(future)):
                    trading_minutes += 5
                    high = future.high[j]
                    low = future.low[j]
                    close = future.close[j]

                    if low < limit_price:
                        # Won
                        last_exit = future.date[j]
                        simulation_result = simulation_result.append(
                            Series(index=["action", "result", "chart_index", "next_index"], data=[action, open_price - limit_price, i, get_next_index(df,last_exit)]),
                            ignore_index=True)
                        break
                    elif high > stop_price:
                        last_exit = future.date[j]
                        simulation_result = simulation_result.append(
                            Series(index=["action", "result", "chart_index", "next_index"], data=[action, open_price - stop_price, i, get_next_index(df,last_exit)]),
                            ignore_index=True)
                        break

                    if use_isl:
                        if self._ig.is_ready_to_set_intelligent_stop(open_price - low, isl_entry_pip):
                            new_stop_level = close + distance
                            if new_stop_level < stop_price:
                                stop_price = new_stop_level

        return simulation_result

    def calculate_overall_result(self, signals:DataFrame, buy_results: dict, sell_results: dict, min_trades = 70) -> namedtuple:

        wl = 0
        next_index = 0

        trades = 0
        wons = 0
        result = namedtuple('Result', ['wl', 'reward'])
        reward = 0
        for _, signal in signals.iterrows():
            if signal["index"] > next_index:
                if signal.action == TradeAction.BUY:
                    res = buy_results.get(signal["index"])
                elif signal.action == TradeAction.SELL:
                    res = sell_results.get(signal["index"])
                else:
                    res = None

                if res:
                    trades += 1
                    if res['result'] > 0:
                        wons +=1
                    reward += res['result']
                    next_index = res['next_index']
        if trades > min_trades:
            wl = 100 * wons / trades

        return result(wl, reward)


    def simulate_signal(self, signals:DataFrame, df_buy_results: DataFrame, df_sell_results: DataFrame, indicator_name:str) -> DataFrame:

        results = []
        for i in range(len(signals)):
            signal = signals.iloc[i]
            if signal.action == TradeAction.NONE:
                continue

            if signal.action == TradeAction.BUY:
                res = df_buy_results[df_buy_results.chart_index == signal["chart_index"]]
                if len(res) != 0:
                    results.append({"chart_index": signal["chart_index"], indicator_name: res[:1].result.item()})
            elif signal.action == TradeAction.SELL:
                res = df_sell_results[df_sell_results.chart_index == signal["chart_index"]]
                if len(res) != 0:
                    results.append({"chart_index": signal["chart_index"], indicator_name: res[:1].result.item()})
            elif signal.action == TradeAction.BOTH:
                results.append({"chart_index": signal["chart_index"], indicator_name: 0})




        return DataFrame(results)










    @staticmethod
    def _calc_spread(df_train):
        return (abs((df_train.close - df_train.close.shift(1))).median()) * 0.8
