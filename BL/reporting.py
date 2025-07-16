import json
import os.path
import time
import traceback
from typing import Dict, List, Optional
from trading_ig import IGService
from trading_ig.rest import IGException, ApiExceededException
from BL import DataProcessor, BaseReader
from BL.analytics import Analytics
from BL.datatypes import TradeAction
from BL.indicators import Indicators
from BL.trade_types import TradeResult
from Connectors.deal_store import DealStore, Deal
from Connectors.predictore_store import PredictorStore
from Predictors.deep_predictor import DeepPredictor
from Predictors.generic_predictor import GenericPredictor
from Predictors.utils import TimeUtils
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.Tracer import Tracer
import plotly.graph_objects as go
import pandas as pd
from pandas import DataFrame, Series
import re
import tempfile
from datetime import datetime, timedelta
from Connectors.tiingo import TradeType
from UI.base_viewer import BaseViewer



class IgReport:

    def __init__(self, ig_service: IGService, deal_store, tracer: Tracer = ConsoleTracer()):
        self.ig_service = ig_service
        self.tracer = tracer
        self.deal_store = deal_store
        self.data_processor = DataProcessor()
        self.indicators = Indicators()

    def report_last_day(self, ti, cache, dp, analytics, viewer: BaseViewer, days: int = 7):
        start_time = (datetime.now() - timedelta(hours=days * 24))
        start_time_hours = (datetime.now() - timedelta(days=days * 2))
        start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%S")

        hist = self.ig_service.get_transaction_history(start_time)
        if len(hist) == 0:
            return

        hist = hist.set_index("openDateUtc")
        hist.sort_index(inplace=True)
        hist.reset_index(inplace=True)

        hist["openDateUtc"] = pd.to_datetime(hist["openDateUtc"])
        hist["dateUtc"] = pd.to_datetime(hist["dateUtc"])
        hist["openLevel"] = hist["openLevel"].astype("float")
        hist["closeLevel"] = hist["closeLevel"].astype("float")

        hist = self.ig_service.fix_hist(hist)

        for i in [""] + Indicators().get_all_indicator_names():
            print(f"Indicator {i}")
            df_results = DataFrame()
            for ticker in hist['name'].unique():
                df_res = self.report_symbol(ti=ti,
                                            ticker=ticker,
                                            start_time_hours=start_time_hours,
                                            start_time_str=start_time_str,
                                            hist=hist,
                                            cache=cache,
                                            dp=dp,
                                            analytics=analytics,
                                            viewer=viewer,
                                            predictor_settings={"_additional_indicators": [i]})
                df_results = df_results.append(df_res)
            print(df_results)

            # print(df_results.filter(["date","ticker", "wl", "eval_result"]))
            try:
                wl_eval = len(df_results[df_results.eval_result == 'won']) / (
                        len(df_results[df_results.eval_result == 'won']) + len(
                    df_results[df_results.eval_result == 'lost']))
                wl_original = len(df_results[df_results.wl == 'won']) / (
                        len(df_results[df_results.wl == 'won']) + len(df_results[df_results.wl == 'lost']))
                print(f"WL   Original: {wl_original} Eval: {wl_eval}")
                print(
                    f"Lost Original: {len(df_results[df_results.wl == 'lost'])} Eval: {len(df_results[df_results.eval_result == 'lost'])}")
            except:
                print("Division by Zero")

    def report_summary(self,
                       ti,
                       dp_service,
                       delta: timedelta = timedelta(hours=24),
                       name: str = "lastday"):
        start_time = (datetime.now() - delta)

        hist = self.ig_service.get_transaction_history(start_time)
        if len(hist) == 0:
            return

        hist = self.ig_service.fix_hist(hist)

        summary_text = f"Summary {name}"

        all_profit = hist.profitAndLoss.sum()
        balance = self.ig_service.get_current_balance()

        profit_percentige = (balance * 100 / (balance - all_profit)) - 100

        summary_text += f"\n\rProfit: {all_profit}€"
        summary_text += f"\n\rPerformance: {profit_percentige}%"
        summary_text += f"\n\rWin_Loss: {len(hist[hist.profitAndLoss > 0]) / len(hist)}"
        summary_text += f"\n\r|Ticker| Profit| Mean |"
        summary_text += f"\n\r|------| ------| ---- |"
        for ticker in hist['name'].unique():
            temp_hist = hist[hist['name'] == ticker]
            profit = temp_hist.profitAndLoss.sum()
            mean = temp_hist.profitAndLoss.mean()
            summary_text += f"\n|{ticker}| {profit} | {mean}"

        temp_file = os.path.join(tempfile.gettempdir(), f"summary_{name}.md")

        with open(temp_file, "w") as f:
            f.write(summary_text)

        dp_service.upload_file(temp_file, f"{datetime.now().strftime('%Y_%m_%d')}/summary_{name}.md")

        return

    def create_report(self, ti, dp_service, predictor, cache, dp, analytics, viewer: BaseViewer):
        # self.report_summary(ti, dp_service, timedelta(hours=24), "lastday")
        # self.report_summary(ti=ti,
        #                     dp_service=dp_service,
        #                     delta=timedelta(days=7),
        #                     name="lastweek")
        self.report_last_day(ti=ti, cache=cache, dp=dp, analytics=analytics, viewer=viewer, days=8)

    @staticmethod
    def _print_open(fig, df, symbol):
        fig.add_scatter(x=df["openDateUtc"],
                        y=df["openLevel"],
                        marker=dict(
                            color='Blue',
                            size=10,
                            symbol=symbol
                        ),
                        )

    @staticmethod
    def _print_result(fig, df, color):
        fig.add_scatter(x=df["dateUtc"],
                        y=df["closeLevel"],
                        marker=dict(
                            color=color,
                            size=10
                        ),
                        )

    @staticmethod
    def _print_win(fig, df):
        IgReport._print_result(fig, df, "Green")

    @staticmethod
    def _print_loose(fig, df):
        IgReport._print_result(fig, df, "Red")

    @staticmethod
    def _print_long_open(fig, df):
        IgReport._print_open(fig, df, "triangle-up")

    @staticmethod
    def _print_short_open(fig, df):
        IgReport._print_open(fig, df, "triangle-down")

    @staticmethod
    def _print_stop_limit():
        pass
        # stopLine, = plt.plot([row.openDateUtc, row.dateUtc], [row.openLevel + pl, row.openLevel + pl],
        #                     color="#ff0000")
        # limitLine, = plt.plot([row.openDateUtc, row.dateUtc], [row.openLevel - pl, row.openLevel - pl],
        #                      color="#00ff00", label="Limit")

    @staticmethod
    def report_symbol(ti, ticker, start_time_hours, start_time_str, hist, cache, dp, analytics: Analytics,
                      viewer: BaseViewer, predictor_settings: Dict):
        df_results = DataFrame()
        df_history = ti.load_data_by_date(ticker,
                                          TimeUtils.get_date_string(start_time_hours),
                                          None,
                                          DataProcessor(),
                                          validate=False)

        df_hour = df_history[df_history["date"] > start_time_str]

        temp_hist = hist[hist['name'] == ticker]

        add_text = ""
        for r in temp_hist.iterrows():
            row = r[1]
            t = (str(row.openDateUtc)).replace(" ", "T")
            n = row["name"]
            name = f"{t}_{n}"
            deal_info = cache.load_deal_info(name)
            if deal_info != None:
                win_lost = deal_info["_wins"] / deal_info["_trades"]
                add_text += f"{deal_info['Type']}: WL: {win_lost} - Trades: {deal_info['_trades']}"
                predictor = GenericPredictor(indicators=Indicators(), symbol="")
                predictor.setup(deal_info)
                predictor.setup(predictor_settings)
                df, df_eval = ti.load_train_data(n, dp, TradeType.FX)
                dt = datetime.fromisoformat(str(row.openDateUtc))
                filter = datetime(dt.year, dt.month, dt.day, dt.hour) - timedelta(hours=1)
                open_data = (df[df.date == TimeUtils.get_time_string(filter)]).iloc[0]
                open_data["predictor"] = deal_info['Type']
                open_data["ticker"] = ticker
                if row.profitAndLoss > 0:
                    open_data["wl"] = "won"
                else:
                    open_data["wl"] = "lost"
                open_data["action"] = deal_info["direction"].lower()
                open_data["eval_result"] = "none"
                open_data["eval_action"] = "none"
                open_data["trades"] = deal_info["_trades"]
                open_data["wl_ration"] = win_lost

                df_results = df_results.append(open_data)
                res = analytics.evaluate(predictor, df, df_eval, name,
                                         time_filter=datetime(dt.year, dt.month, dt.day, dt.hour))
                for trade in res.get_trade_results():
                    if TimeUtils.get_time_string(datetime(dt.year, dt.month, dt.day, dt.hour)) == trade.open_time:
                        df_results.loc[
                            df_results.date == TimeUtils.get_time_string(filter), "eval_result"] = trade.result
                        df_results.loc[
                            df_results.date == TimeUtils.get_time_string(filter), "eval_action"] = trade.action
            else:
                raise Exception()

        winner = temp_hist[temp_hist["profitAndLoss"] >= 0]
        looser = temp_hist[temp_hist["profitAndLoss"] < 0]

        long_winner = winner[winner["closeLevel"] >= winner["openLevel"]]
        short_winner = winner[winner["closeLevel"] <= winner["openLevel"]]

        long_looser = looser[looser["closeLevel"] < looser["openLevel"]]
        short_looser = looser[looser["closeLevel"] > looser["openLevel"]]

        shorts = short_winner.append(short_looser)
        longs = long_winner.append(long_looser)

        fig = go.Figure(data=[
            go.Candlestick(x=df_hour['date'],
                           open=df_hour['open'],
                           high=df_hour['high'],
                           low=df_hour['low'],
                           close=df_hour['close']),
        ])

        # Open
        IgReport._print_long_open(fig, longs)
        IgReport._print_short_open(fig, shorts)

        # result
        IgReport._print_win(fig, winner)
        IgReport._print_loose(fig, looser)

        fig.update_layout(
            title=f"Live trade of  <a href='https://de.tradingview.com/chart/?symbol={ticker}'>{ticker}</a> {add_text}",
            legend_title="Legend Title",
        )
        fig.show()

        # if len(df_results[df_results.action != df_results.eval_action]) > 0:
        #     print(f"{ticker} ERROR- action mismatch")
        #
        # if len(df_results[df_results.wl != df_results.eval_result]) > 0:
        #     print(f"{ticker} ERROR - evaluation mismatch")
        return df_results