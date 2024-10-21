import datetime
import sys
from collections import namedtuple

from tqdm import tqdm

from BL import measure_time
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
                 epic: str,
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

        distance, adapted = self._ig.get_stop_distance(market, epic, scaling, check_min=True,
                                              intelligent_stop_distance=predictor.get_isl_distance())

        for i in range(len(df) - 4):
            current_index = i + 1



            action = predictor.predict(df[:current_index])
            if action == TradeAction.NONE:
                continue

            if action == TradeAction.BOTH:
                trades.append(TradeResult(action, 0, i))
                continue

            open_price = df.close[current_index - 1]
            trade = TradeResult(action=action, open_time=df.date[current_index], opening=open_price)
            trades.append(trade)

            close_price = df.close[current_index + 3]

            if action == TradeAction.BUY:



                trade.set_result(profit=market.get_euro_value(close_price - open_price, scaling), closing=close_price,
                                 close_time=last_exit)


            elif action == TradeAction.SELL:
                trade.set_result(profit=market.get_euro_value(open_price - close_price, scaling), closing=close_price,
                                 close_time=last_exit)

        predictor._tracer = old_tracer
        ev_res = EvalResult(symbol=symbol, trades_results=trades,
                            len_df=len(df), trade_minutes=trading_minutes,
                            scan_time=datetime.datetime.now(), adapted_isl_distance=adapted)

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
                 epic: str,
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

        stop_pip = market.get_pip_value(stop_euro, scaling)
        limit_pip = market.get_pip_value(limit_euro, scaling)
        isl_entry_pip = market.get_pip_value(isl_entry, scaling)
        isl_stop_distance, adapted = self._ig.get_stop_distance(market, epic, scaling, check_min=True,
                                              intelligent_stop_distance=isl_distance)

        for i in range(len(df) - 4):
            current_index = i + 1
            open_price = df.close[current_index - 1]
            future = df_eval[pd.to_datetime(df_eval["date"]) > pd.to_datetime(df.date[i]) + timedelta(hours=1)]
            future.reset_index(inplace=True, drop=True)

            if action == TradeAction.BUY:
                close_price = df.close[current_index +3]

                simulation_result = simulation_result.append(Series(index=["action", "result", "chart_index", "houres"],
                                                                    data=[action, close_price - open_price, i, 3]),
                                                             ignore_index=True)

            elif action == TradeAction.SELL:
                close_price = df.close[current_index + 3]

                simulation_result = simulation_result.append(Series(index=["action", "result", "chart_index", "houres"],
                                                                    data=[action, open_price - close_price, i, 3]),
                                                             ignore_index=True)

        return simulation_result

    def calculate_overall_result(self, signals:DataFrame, buy_results: dict, sell_results: dict, min_trades = 70) -> namedtuple:
        result = namedtuple('Result', ['wl', 'reward'])
        trades = wons = reward = 0

        # Verwende numpy um den iterativen Ansatz zu beschleunigen
        for signal in signals.itertuples():
            res = None
            if signal.action == TradeAction.BUY:
                res = buy_results.get(signal.index)
            elif signal.action == TradeAction.SELL:
                res = sell_results.get(signal.index)

            if res:
                trades += 1
                reward += res['result']
                wons += 1 if res['result'] > 0 else 0

        wl = (100 * wons / trades) if trades > min_trades else 0

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
