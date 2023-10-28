import os.path
import time
from typing import List, Dict

from trading_ig import IGService
from trading_ig.rest import IGException
from BL import DataProcessor, timedelta, BaseReader
from BL.analytics import Analytics
from BL.indicators import Indicators
from Predictors.generic_predictor import GenericPredictor
from Predictors.utils import TimeUtils
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.Tracer import Tracer
import plotly.graph_objects as go
import pandas as pd
from pandas import DataFrame
import re
import tempfile
from datetime import datetime
from Connectors.tiingo import TradeType
from UI.base_viewer import BaseViewer
from UI.plotly_viewer import PlotlyViewer


class IG:

    def __init__(self, conf_reader: BaseReader, tracer: Tracer = ConsoleTracer(), live: bool = False):
        self.ig_service: IGService = None
        self.user = conf_reader.get("ig_demo_user")
        self.password = conf_reader.get("ig_demo_pass")
        self.key = conf_reader.get("ig_demo_key")
        self.accNr = conf_reader.get("ig_demo_acc_nr")
        if live:
            self.type = "LIVE"
            self._fx_id = 342535
            self._crypto_id = None
            self._gold_id = None
            self._silver_id = None
        else:
            self.type = "DEMO"
            self._fx_id = 264139
            self._crypto_id = 1002200
            self._gold_id = 104139
            self._silver_id = 264211
        self._tracer: Tracer = tracer
        self.connect()
        self._excludedMarkets = ["CHFHUF", "EMFX USDTWD ($1 Contract)", "EMFX USDPHP ($1 Contract)",
                                 "EMFX USDKRW ($1 Contract)",
                                 "EMFX USDINR ($1 Contract)", "EMFX USDIDR ($1 Contract)", "EMFX INRJPY",
                                 "EMFX GBPINR (1 Contract)", "NZDGBP",
                                 "NZDEUR", "NZDAUD", "AUDGBP", "AUDEUR", "GBPEUR"]

        self._symbol_reference = {
            "CS.D.BCHUSD.CFD.IP":
                {
                    "symbol": "BCHUSD",
                    "size": 1,
                    "currency": "USD"
                },
            "CS.D.BCHUSD.CFE.IP":
                {
                    "symbol": "BCHEUR",
                    "size": 1,
                    "currency": "EUR"
                },
            # Gold
            "CS.D.CFDGOLD.CFDGC.IP":
                {
                    "symbol": "XAUUSD",
                    "size": 1,
                    "currency": "USD"
                },
            # Silber
            "CS.D.CFDSILVER.CFM.IP":
                {
                    "symbol": "XAGUSD",
                    "size": 0.5,
                    "currency": "USD"
                }
        }

    def _get_markets_by_id(self, id):
        try:
            res = self.ig_service.fetch_sub_nodes_by_node(id)
        except Exception:
            self._tracer.error("Error while fetching nodes")
            time.sleep(10)
            return DataFrame()

        if len(res["nodes"]) > 0:
            markets = DataFrame()
            for i in res["nodes"].id:
                markets = markets.append(self._get_markets_by_id(i))
            return markets
        else:
            return res["markets"]

    def _set_symbol(self, markets):
        for m in markets:
            epic = m["epic"]
            if epic in self._symbol_reference:
                m["symbol"] = self._symbol_reference[epic]["symbol"]
                m["size"] = self._symbol_reference[epic]["size"]
                m["currency"] = self._symbol_reference[epic]["currency"]

        return markets

    def get_markets(self, trade_type: TradeType, tradeable: bool = True) -> DataFrame:
        if trade_type == TradeType.FX:
            return self._get_markets(self._fx_id, tradeable)
        elif trade_type == TradeType.CRYPTO:
            markets = self._get_markets(self._crypto_id, tradeable)  # 668997 is only Bitcoin Cash
            return self._set_symbol(markets)
        elif trade_type == TradeType.METAL:
            gold = self._get_markets(self._gold_id, tradeable)  # Gold
            silver = self._get_markets(self._silver_id, tradeable)
            return self._set_symbol(gold + silver)

        return DataFrame()

    def _get_spread(self, market_object):
        offer = market_object.offer
        bid = market_object.bid
        scaling = market_object.scalingFactor

        if offer is not None and bid is not None:
            return (offer - bid) * scaling

        return 0

    def _get_markets(self, id: int, tradebale: bool = True):
        market_df = self._get_markets_by_id(id)
        if len(market_df) == 0:
            return DataFrame()

        markets = []
        if tradebale:
            market_df = market_df[market_df.marketStatus == "TRADEABLE"]
        for market in market_df.iterrows():
            symbol = (market[1].instrumentName.replace("/", "").replace(" Mini", "")).strip()
            if symbol not in self._excludedMarkets:
                markets.append({
                    "symbol": symbol,
                    "epic": market[1].epic,
                    "spread": self._get_spread(market[1]),
                    "scaling": market[1].scalingFactor,
                    "size": 1.0,
                    "currency": self.get_currency(market[1].epic)
                })

        return markets

    def connect(self):
        # no cache
        self.ig_service = IGService(
            self.user, self.password, self.key, self.type, acc_number=self.accNr
        )
        try:
            self.ig_service.create_session()
        except Exception as ex:
            self._tracer.error(f"Error during open a IG Connection {ex}")

    @staticmethod
    def get_currency(epic: str):
        m = re.match("[\w]+\.[\w]+\.[\w]{3}([\w]{3})\.", epic)
        if m != None and len(m.groups()) == 1:
            return m.groups()[0]
        return "USD"

    def buy(self,
            epic: str,
            stop: int,
            limit: int,
            size: float = 1.0,
            currency: str = "USD") -> (bool, str):
        return self.open(epic, "BUY", stop, limit, size, currency)

    def sell(self,
             epic: str,
             stop: int,
             limit: int,
             size: float = 1.0,
             currency: str = "USD") -> (bool, str):
        return self.open(epic, "SELL", stop, limit, size, currency)

    def open(self,
             epic: str,
             direction: str,
             stop: int = 25,
             limit: int = 25,
             size: float = 1.0,
             currency: str = "USD") -> (bool, dict):

        deal_response: dict = {}
        result = False
        try:
            response = self.ig_service.create_open_position(
                currency_code=currency,
                direction=direction,
                epic=epic,
                expiry="-",
                force_open=True,
                guaranteed_stop=False,
                order_type="MARKET",
                size=size,
                level=None,
                limit_distance=limit,
                limit_level=None,
                quote_id=None,
                stop_distance=stop,
                stop_level=None,
                trailing_stop=False,
                trailing_stop_increment=None
            )
            if response["dealStatus"] != "ACCEPTED":
                self._tracer.error(f"could not open trade: {response['reason']} for {epic}")
            else:
                self._tracer.write(f"Opened successfull {epic}. Deal details {response}")
                result = True
            deal_response = response
        except IGException as ex:
            self._tracer.error(f"Error during open a position. {ex} for {epic}")

        return result, deal_response

    def close(self,
              epic: str,
              direction: str,
              deal_id: str,
              size: float = 1.0, ) -> (bool, dict):

        deal_response: dict = {}
        result = False
        try:
            response = self.ig_service.close_open_position(
                direction=direction,
                epic=epic,
                expiry="-",
                order_type="MARKET",
                size=size,
                level=None,
                quote_id=None,
                deal_id=deal_id
            )
            if response["dealStatus"] != "ACCEPTED":
                self._tracer.error(f"could not close trade: {response['reason']} for {epic}")
            else:
                self._tracer.write(f"Close successfull {epic}. Deal details {response}")
                result = True
            deal_response = response
        except IGException as ex:
            self._tracer.error(f"Error during close a position. {ex} for {epic}")

        return result, deal_response

    @staticmethod
    def get_inverse(direction: str) -> str:
        if direction == "SELL":
            return "BUY"
        else:
            return "SELL"

    def has_opened_positions(self):
        positions = self.ig_service.fetch_open_positions()
        return len(positions) > 0

    def get_opened_position_ids_by_direction(self, direction: str):
        positions = self.ig_service.fetch_open_positions()
        return positions.loc[positions["direction"] == direction]

    def get_opened_positions(self) -> DataFrame:
        return self.ig_service.fetch_open_positions()

    def get_opened_positions_by_epic(self, epic: str) -> DataFrame:
        positions = self.get_opened_positions()
        return positions[positions.epic == epic]

    def get_transaction_history(self, start_time: str):
        return self.ig_service.fetch_transaction_history(trans_type="ALL_DEAL", from_date=start_time,
                                                         max_span_seconds=60 * 50)

    def get_current_balance(self):
        balance = self.ig_service.fetch_accounts().loc[0].balance
        if balance == None:
            return 0
        return balance

    @staticmethod
    def _get_hours(start_date):
        start_time = pd.to_datetime(start_date.openDateUtc.values[0])
        first_hours = datetime(start_time.year, start_time.month, start_time.day, start_time.hour)
        hours = [first_hours]
        for i in range(23):
            hours.append(hours[i] + timedelta(hours=1))

        return hours

    @staticmethod
    def fix_hist(hist):
        new_column = []
        for values in hist.instrumentName:
            res = re.search(r'\w{3}\/\w{3}', values)
            if res is not None:
                new_column.append(re.search(r'\w{3}\/\w{3}', values).group().replace("/", ""))
            else:
                new_column.append("Unknown")
        hist['name'] = new_column

        hist['profitAndLoss'] = hist.profitAndLoss.str.replace("E", "").astype(float)

        return hist

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
        IG._print_result(fig, df, "Green")

    @staticmethod
    def _print_loose(fig, df):
        IG._print_result(fig, df, "Red")

    @staticmethod
    def _print_long_open(fig, df):
        IG._print_open(fig, df, "triangle-up")

    @staticmethod
    def _print_short_open(fig, df):
        IG._print_open(fig, df, "triangle-down")

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
                predictor = GenericPredictor(indicators=Indicators())
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
                res = analytics.evaluate(predictor, df, df_eval, name, viewer,
                                         filter=datetime(dt.year, dt.month, dt.day, dt.hour))
                for trade in res._trade_results:
                    if TimeUtils.get_time_string(datetime(dt.year, dt.month, dt.day, dt.hour)) == trade.last_df_time:
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
        IG._print_long_open(fig, longs)
        IG._print_short_open(fig, shorts)

        # result
        IG._print_win(fig, winner)
        IG._print_loose(fig, looser)

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

    def report_last_day(self, ti, cache, dp, analytics, viewer: BaseViewer, days: int = 7):
        start_time = (datetime.now() - timedelta(hours=days * 24))
        start_time_hours = (datetime.now() - timedelta(days=days * 2))
        start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%S")

        hist = self.get_transaction_history(start_time)
        if len(hist) == 0:
            return

        hist = hist.set_index("openDateUtc")
        hist.sort_index(inplace=True)
        hist.reset_index(inplace=True)

        hist["openDateUtc"] = pd.to_datetime(hist["openDateUtc"])
        hist["dateUtc"] = pd.to_datetime(hist["dateUtc"])
        hist["openLevel"] = hist["openLevel"].astype("float")
        hist["closeLevel"] = hist["closeLevel"].astype("float")

        hist = self.fix_hist(hist)

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

        hist = self.get_transaction_history(start_time)
        if len(hist) == 0:
            return

        hist = self.fix_hist(hist)

        summary_text = f"Summary {name}"

        all_profit = hist.profitAndLoss.sum()
        balance = self.get_current_balance()

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
