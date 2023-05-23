import os.path
from trading_ig import IGService
from trading_ig.rest import IGException
from BL.data_processor import DataProcessor
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.Tracer import Tracer
import plotly.graph_objects as go
import pandas as pd
from pandas import DataFrame
import re
from BL.utils import *
import tempfile
from datetime import datetime
from Connectors.tiingo import TradeType


class IG:

    def __init__(self, conf_reader: BaseReader, tracer: Tracer = ConsoleTracer(), live: bool = False):
        self.ig_service = None
        self.user = conf_reader.get("ig_demo_user")
        self.password = conf_reader.get("ig_demo_pass")
        self.key = conf_reader.get("ig_demo_key")
        self.accNr = conf_reader.get("ig_demo_acc_nr")
        if live:
            self.type = "LIVE"
        else:
            self.type = "DEMO"
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
        res = self.ig_service.fetch_sub_nodes_by_node(id)
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
            return self._get_markets(264139, tradeable)
        elif trade_type == TradeType.CRYPTO:
            markets = self._get_markets(1002200, tradeable)  # 668997 is only Bitcoin Cash
            return self._set_symbol(markets)
        elif trade_type == TradeType.METAL:
            gold = self._get_markets(104139, tradeable)  # Gold
            silver = self._get_markets(264211, tradeable)
            return self._set_symbol(gold + silver)

        return DataFrame()

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
                    "spread": (market[1].offer - market[1].bid) * market[1].scalingFactor,
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

    def get_currency(self, epic: str):
        m = re.match("[\w]+\.[\w]+\.[\w]{3}([\w]{3})\.", epic)
        if m != None and len(m.groups()) == 1:
            return m.groups()[0]
        return "USD"

    def buy(self, epic: str, stop: int, limit: int, size: float = 1.0, currency: str = "USD"):
        return self.open(epic, "BUY", stop, limit, size, currency)

    def sell(self, epic: str, stop: int, limit: int, size: float = 1.0, currency: str = "USD"):
        return self.open(epic, "SELL", stop, limit, size, currency)

    def open(self, epic: str, direction: str, stop: int = 25, limit: int = 25, size: float = 1.0,
             currency: str = "USD") -> bool:
        deal_reference = None
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
                self._tracer.write(f"{direction} {epic} with limit {limit} and stop {stop}")
                deal_reference = response["dealReference"]
                result = True
        except IGException as ex:
            self._tracer.error(f"Error during open a position. {ex} for {epic}")

        return result, deal_reference

    def has_opened_positions(self):
        positions = self.ig_service.fetch_open_positions()
        return len(positions) > 0

    def get_opened_position_ids_by_direction(self, direction: str):
        positions = self.ig_service.fetch_open_positions()
        return positions.loc[positions["direction"] == direction]

    def get_opened_positions(self):
        return self.ig_service.fetch_open_positions()

    def get_opened_positions_by_epic(self, epic: str):
        positions = self.get_opened_positions()
        epics = positions[positions.epic == epic]
        if len(epics) == 1:
            return epics.loc[0]
        else:
            return None

    def get_transaction_history(self, start_time: str):
        return self.ig_service.fetch_transaction_history(trans_type="ALL_DEAL", from_date=start_time,
                                                         max_span_seconds=60 * 50)

    def get_current_balance(self):
        return self.ig_service.fetch_accounts().loc[0].balance

    def exit(self, deal_id: str, direction: str):
        response = self.ig_service.close_open_position(
            deal_id=deal_id,
            direction=direction,
            epic=None,
            expiry="-",
            order_type="MARKET",
            size=1,
            level=None,
            quote_id=None
        )

    def _get_hours(self, start_date):
        start_time = pd.to_datetime(start_date.openDateUtc.values[0])
        first_hours = datetime(start_time.year, start_time.month, start_time.day, start_time.hour)
        hours = [first_hours]
        for i in range(23):
            hours.append(hours[i] + timedelta(hours=1))

        return hours

    def fix_hist(self, hist):
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

    def report_last_day(self, ti, dp_service):
        start_time = (datetime.now() - timedelta(hours=60))
        start_time_hours = (datetime.now() - timedelta(hours=200))
        start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%S")

        hist = self.get_transaction_history(start_time)
        if len(hist) == 0:
            return

        hist = hist.set_index("openDateUtc")
        hist.sort_index(inplace=True)
        hist.reset_index(inplace=True)

        # hist['profitAndLoss'] = hist['profitAndLoss'].str.replace('E', '', regex=True).astype('float64')
        hist["openDateUtc"] = pd.to_datetime(hist["openDateUtc"])
        hist["dateUtc"] = pd.to_datetime(hist["dateUtc"])
        hist["openLevel"] = hist["openLevel"].astype("float")
        hist["closeLevel"] = hist["closeLevel"].astype("float")

        hist = self.fix_hist(hist)

        for ticker in hist['name'].unique():

            df_min = ti.load_data_by_date(ticker, start_time.strftime("%Y-%m-%d"),
                                          None, DataProcessor(), "1min", False, False)
            df_hour = ti.load_data_by_date(ticker, start_time_hours.strftime("%Y-%m-%d"),
                                           None, DataProcessor())
            if len(df_min) == 0:
                continue

            df_min = df_min[df_min["date"] > start_time_str]
            df_hour = df_hour[df_hour["date"] > start_time_str]

            temp_hist = hist[hist['name'] == ticker]

            df_min = df_min.filter(["close", "date"])

            winner = temp_hist[temp_hist["profitAndLoss"] >= 0]
            looser = temp_hist[temp_hist["profitAndLoss"] < 0]

            long_winner = winner[winner["closeLevel"] >= winner["openLevel"]]
            short_winner = winner[winner["closeLevel"] <= winner["openLevel"]]

            long_looser = looser[looser["closeLevel"] < looser["openLevel"]]
            short_looser = looser[looser["closeLevel"] > looser["openLevel"]]

            shorts = short_winner.append(short_looser)
            longs = long_winner.append(long_looser)

            fig = go.Figure(data=[
                go.Line(x=df_min['date'], y=df_min["close"],
                        line=dict(shape='linear', color='Gray')),
                go.Line(x=df_hour['date'], y=df_hour["BB_LOWER"],
                        line=dict(shape='linear', color='Orange')),
                go.Line(x=df_hour['date'], y=df_hour["BB_UPPER"],
                        line=dict(shape='linear', color='Orange')),
                go.Candlestick(x=df_hour['date'],
                               open=df_hour['open'],
                               high=df_hour['high'],
                               low=df_hour['low'],
                               close=df_hour['close']),
            ])
            for i in range(len(shorts)):
                row = shorts[i:i + 1]
                pl = row.openLevel - row.closeLevel

                # stopLine, = plt.plot([row.openDateUtc, row.dateUtc], [row.openLevel + pl, row.openLevel + pl],
                #                     color="#ff0000")
                # limitLine, = plt.plot([row.openDateUtc, row.dateUtc], [row.openLevel - pl, row.openLevel - pl],
                #                      color="#00ff00", label="Limit")

            for i in range(len(longs)):
                row = longs[i:i + 1]
                pl = row.closeLevel - row.openLevel

                # plt.plot([row.openDateUtc, row.dateUtc], [row.openLevel + pl, row.openLevel + pl], color="#ff0000")
                # plt.plot([row.openDateUtc, row.dateUtc], [row.openLevel - pl, row.openLevel - pl], color="#00ff00")

            # long open
            fig.add_scatter(x=long_winner["openDateUtc"],
                            y=long_winner["openLevel"],
                            marker=dict(
                                color='Blue',
                                size=10,
                                symbol="triangle-up"
                            ),
                            )
            fig.add_scatter(x=long_looser["openDateUtc"],
                            y=long_looser["openLevel"],
                            marker=dict(
                                color='Blue',
                                size=10,
                                symbol="triangle-up"
                            ),
                            )

            # short open
            fig.add_scatter(x=short_winner["openDateUtc"],
                            y=short_winner["openLevel"],
                            marker=dict(
                                color='Blue',
                                size=10,
                                symbol="triangle-down"
                            ),
                            )
            fig.add_scatter(x=short_looser["openDateUtc"],
                            y=short_looser["openLevel"],
                            marker=dict(
                                color='Blue',
                                size=10,
                                symbol="triangle-down"
                            ),
                            )

            # long close
            fig.add_scatter(x=long_winner["dateUtc"],
                            y=long_winner["closeLevel"],
                            marker=dict(
                                color='Green',
                                size=10
                            ),
                            )
            fig.add_scatter(x=long_looser["dateUtc"],
                            y=long_looser["closeLevel"],
                            marker=dict(
                                color='Red',
                                size=10
                            ),
                            )

            # short close
            fig.add_scatter(x=short_winner["dateUtc"],
                            y=short_winner["closeLevel"],
                            marker=dict(
                                color='Green',
                                size=10
                            ),
                            )
            fig.add_scatter(x=short_looser["dateUtc"],
                            y=short_looser["closeLevel"],
                            marker=dict(
                                color='Red',
                                size=10
                            ),
                            )

            fig.update_layout(
                title=ticker,
                legend_title="Legend Title",
            )
            fig.show()

            hours = self._get_hours(temp_hist[0:1])

        # tempng = os.path.join(tempfile.gettempdir(), f"{ticker}.png")

        # dp_service.upload(tempng,
        #                  os.path.join(
        #                      datetime.now().strftime("%Y_%m_%d"),
        #                      f"{ticker}.png"))

    def report_summary(self, ti, dp_service, delta: timedelta = timedelta(hours=24), name: str = "lastday"):
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

        dp_service.upload_file(temp_file, os.path.join(
            datetime.now().strftime("%Y_%m_%d"),
            f"summary_{name}.md"))

        return

    def create_report(self, ti, dp_service):
        # self.report_summary(ti, dp_service, timedelta(hours=24), "lastday")
        # self.report_summary(ti, dp_service, timedelta(days=7), "lastweek")
        self.report_last_day(ti, dp_service)
