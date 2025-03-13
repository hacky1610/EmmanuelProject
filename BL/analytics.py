import sys
from collections import namedtuple
from Connectors.market_store import MarketStore
from Tracing.Tracer import Tracer
from Tracing.ConsoleTracer import ConsoleTracer
from pandas import DataFrame, Series
from BL.datatypes import TradeAction
import pandas as pd
from datetime import timedelta


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



    def get_signals(self, predictor,
                 df: DataFrame) -> DataFrame:

        assert len(df) > 0

        trades = DataFrame()

        predictor.init_caches(df)

        for i in range(len(df) - 1):
            current_index = i + 1
            action = predictor.predict(df[:current_index])

            if action != TradeAction.NONE:
                new_trade = pd.Series(
                    data=[action, i],
                    index=["action", "chart_index"]
                )

                # Concatenate the new trade to the existing trades DataFrame
                trades = pd.concat([trades, new_trade.to_frame().T], ignore_index=True)

        return trades

    def simulate(self,
                 action:str,
                 epic: str,
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

        stop_pip = df.ATR.iloc[-1] * 1.5
        limit_pip = df.ATR.iloc[-1] * 1.5
        isl_entry_pip = market.get_pip_value(isl_entry, scaling)
        isl_stop_distance, adapted = self._ig.get_stop_distance(market, epic, scaling, check_min=True,
                                              intelligent_stop_distance=isl_distance)

        max_hold_time = timedelta(hours=12)

        for i in range(len(df) - 1):
            current_index = i + 1
            open_price = df.close[current_index - 1]
            future = df_eval[pd.to_datetime(df_eval["date"]) > pd.to_datetime(df.date[i]) + timedelta(hours=1)]
            future.reset_index(inplace=True, drop=True)

            # Filter the future dataframe based on max_hold_time
            future = future[pd.to_datetime(future["date"]) <= pd.to_datetime(df.date[i]) + max_hold_time]


            if action == TradeAction.BUY:
                open_price = open_price + spread
                if isl_open_end:
                    limit_price = sys.float_info.max
                else:
                    limit_price = open_price + limit_pip
                stop_price = open_price - stop_pip

                n  = None

                for j in range(len(future)):
                    trading_minutes += 5
                    high = future.high[j]
                    low = future.low[j]
                    close = future.close[j]

                    if high > limit_price:
                        # Won
                        last_exit = future.date[j]

                        n = Series(index=["action","result","chart_index", "next_index"],
                                                                            data=[action,limit_price - open_price,i, get_next_index(df,last_exit)])
                        break
                    elif low < stop_price:
                        # Loss
                        last_exit = future.date[j]
                        n = Series(index=["action", "result", "chart_index", "next_index"],
                                   data=[action, stop_price - open_price, i,get_next_index(df,last_exit)])
                        break

                    if use_isl:
                        if self._ig.is_ready_to_set_intelligent_stop(high - open_price, isl_entry_pip):
                            new_stop_level = close - isl_stop_distance
                            if new_stop_level > stop_price:
                                stop_price = new_stop_level

                if n is not None:
                    simulation_result = pd.concat([simulation_result, pd.DataFrame([n])], ignore_index=True)
                else:
                    new_row = pd.DataFrame([{"action": action, "result": -1, "chart_index": i, "next_index": -1}])

                    # Verwenden von pd.concat, um die neue Zeile hinzuzufügen
                    simulation_result = pd.concat([simulation_result, new_row], ignore_index=True)





            elif action == TradeAction.SELL:
                open_price = open_price - spread
                if isl_open_end:
                    limit_price = sys.float_info.min
                else:
                    limit_price = open_price - limit_pip
                stop_price = open_price + stop_pip

                n = None
                for j in range(len(future)):
                    trading_minutes += 5
                    high = future.high[j]
                    low = future.low[j]
                    close = future.close[j]

                    if low < limit_price:
                        # Won
                        last_exit = future.date[j]
                        n = Series(index=["action", "result", "chart_index", "next_index"], data=[action, open_price - limit_price, i, get_next_index(df,last_exit)])
                        break
                    elif high > stop_price:
                        last_exit = future.date[j]
                        n = Series(index=["action", "result", "chart_index", "next_index"], data=[action, open_price - stop_price, i, get_next_index(df,last_exit)])
                        break

                    if use_isl:
                        if self._ig.is_ready_to_set_intelligent_stop(open_price - low, isl_entry_pip):
                            new_stop_level = close + isl_stop_distance
                            if new_stop_level < stop_price:
                                stop_price = new_stop_level
            if n is not None:
                simulation_result = pd.concat([simulation_result, pd.DataFrame([n])], ignore_index=True)
            else:
                new_row = pd.DataFrame([{"action": action, "result": -1, "chart_index": i, "next_index": -1}])

                # Verwenden von pd.concat, um die neue Zeile hinzuzufügen
                simulation_result = pd.concat([simulation_result, new_row], ignore_index=True)



        return simulation_result



    def calculate_overall_result(self, signals:DataFrame, buy_results: dict, sell_results: dict, min_trades = 50) -> namedtuple:
        result = namedtuple('Result', ['wl', 'reward', "trades", 'wons'])
        trades = wons = reward = 0
        next_index = 0

        # Verwende numpy um den iterativen Ansatz zu beschleunigen
        for signal in signals.itertuples():
            if signal.index > next_index:
                res = None
                if signal.action == TradeAction.BUY:
                    res = buy_results.get(signal.index)
                elif signal.action == TradeAction.SELL:
                    res = sell_results.get(signal.index)

                if res:
                    trades += 1
                    reward += res['result']
                    wons += 1 if res['result'] > 0 else 0
                    next_index = res['next_index']

        wl = (100 * wons / trades) if trades > min_trades else 0

        return result(wl, reward, trades, wons)





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
