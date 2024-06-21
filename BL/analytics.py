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
                 time_filter=None) -> EvalResult:

        assert len(df) > 0
        assert len(df_eval) > 0

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


        for i in range(len(df) - 1):
            current_index = i + 1
            if time_filter is not None and TimeUtils.get_time_string(time_filter) != df.date[current_index]:
                continue

            open_price = df.open[current_index]

            if only_one_position and df.date[i] < last_exit:
                continue

            action = predictor.predict(df[:current_index])
            if action == TradeAction.NONE:
                continue

            stop_pip = market.get_pip_value(predictor.get_stop(), scaling)
            limit_pip = market.get_pip_value(predictor.get_limit(), scaling)

            trade = TradeResult(action=action, open_time=df.date[current_index], opening=df.close[current_index])
            trades.append(trade)

            future = df_eval[pd.to_datetime(df_eval["date"]) > pd.to_datetime(df.date[i]) + timedelta(hours=1)]
            future.reset_index(inplace=True, drop=True)

            additonal_text = self._create_additional_info(df.iloc[current_index],
                                                          "RSI", "CCI", "MACD", "SIGNAL", "PSAR")
            additonal_text += df.iloc[current_index].date

            if action == TradeAction.BUY:
                open_price = open_price + spread
                limit_price = open_price + limit_pip
                stop_price = open_price - stop_pip
                viewer.print_buy(df[i + 1:i + 2].index.item(), open_price, additonal_text)

                for j in range(len(future)):
                    trading_minutes += 5
                    high = future.high[j]
                    low = future.low[j]
                    train_index = df[df.date <= future.date[j]][-1:].index.item()

                    if high > limit_price:
                        # Won
                        viewer.print_won(train_index, future.close[j])
                        last_exit = future.date[j]
                        trade.set_result(profit=predictor.get_limit(), closing=high, close_time=last_exit)
                        break
                    elif low < stop_price:
                        # Loss
                        viewer.print_lost(train_index, future.close[j])
                        last_exit = future.date[j]
                        trade.set_result(profit=predictor.get_stop() * -1, closing=low, close_time=last_exit)
                        break
            elif action == TradeAction.SELL:
                open_price = open_price - spread
                limit_price = open_price - limit_pip
                stop_price = open_price + stop_pip
                viewer.print_sell(df[i + 1:i + 2].index.item(), open_price, additonal_text)

                for j in range(len(future)):
                    trading_minutes += 5
                    high = future.high[j]
                    low = future.low[j]
                    train_index = df[df.date <= future.date[j]][-1:].index.item()

                    if low < limit_price:
                        # Won
                        viewer.print_won(train_index, future.close[j])
                        last_exit = future.date[j]
                        trade.set_result(profit=predictor.get_limit(), closing=high, close_time=last_exit)
                        break
                    elif high > stop_price:
                        viewer.print_lost(train_index, future.close[j])
                        last_exit = future.date[j]
                        trade.set_result( profit= predictor.get_stop() * -1, closing=low, close_time=last_exit)
                        break

        predictor._tracer = old_tracer
        ev_res = EvalResult(trades_results=trades, len_df=len(df), trade_minutes=trading_minutes, scan_time=datetime.datetime.now())
        viewer.update_title(f"{ev_res}")
        viewer.show()

        return ev_res

    @staticmethod
    def _calc_spread(df_train):
        return (abs((df_train.close - df_train.close.shift(1))).median()) * 0.8
