import os.path
from trading_ig import IGService
from trading_ig.rest import IGException
from BL.data_processor import DataProcessor
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.Tracer import Tracer
import matplotlib.pyplot as plt
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
        self._excludedMarkets = ["CHFHUF","EMFX USDTWD ($1 Contract)","EMFX USDPHP ($1 Contract)","EMFX USDKRW ($1 Contract)",
                                 "EMFX USDINR ($1 Contract)","EMFX USDIDR ($1 Contract)","EMFX INRJPY","EMFX GBPINR (1 Contract)","NZDGBP",
                                 "NZDEUR","NZDAUD","AUDGBP","AUDEUR","GBPEUR"]

    def _get_markets_by_id(self, id):
        res = self.ig_service.fetch_sub_nodes_by_node(id)
        if len(res["nodes"]) > 0:
            markets = DataFrame()
            for i in res["nodes"].id:
                markets = markets.append(self._get_markets_by_id(i))
            return markets
        else:
            return res["markets"]

    def get_markets(self,trade_type:TradeType,tradeable:bool=True) -> DataFrame:
        if trade_type == TradeType.FX:
            return self._get_markets(264139,tradeable)
        elif trade_type == TradeType.CRYPTO:
            return self._get_markets(668997, tradeable) #668997 is only Bitcoin

        return DataFrame()


    def _get_markets(self,id:int,tradebale:bool=True):
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
                    "scaling": market[1].scalingFactor})
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

    def get_currency(self,epic:str):
        m = re.match("[\w]+\.[\w]+\.[\w]{3}([\w]{3})\.", epic)
        if m != None and len(m.groups()) == 1:
            return m.groups()[0]
        return "USD"


    def buy(self, epic: str, stop: int, limit: int,size:float = 1.0):
        return self.open(epic, "BUY", stop, limit,size)

    def sell(self, epic: str, stop: int, limit: int,size:float = 1.0):
        return self.open(epic, "SELL", stop, limit,size)


    def open(self, epic: str, direction: str, stop: int = 25, limit: int = 25, size:float = 1.0) -> bool:
        try:
            response = self.ig_service.create_open_position(
                currency_code=self.get_currency(epic),
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
                return False
            self._tracer.write(f"{direction} {epic} with limit {limit} and stop {stop}")
            return True
        except IGException as ex:
            self._tracer.error(f"Error during open a position. {ex} for {epic}")
            return False

    def has_opened_positions(self):
        positions = self.ig_service.fetch_open_positions()
        return len(positions) > 0

    def get_opened_position_ids_by_direction(self, direction: str):
        positions = self.ig_service.fetch_open_positions()
        return positions.loc[positions["direction"] == direction]

    def get_opened_positions(self):
        return self.ig_service.fetch_open_positions()

    def get_opened_positions_by_epic(self,epic:str):
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

    def fix_hist(self,hist):
        new_column = []
        for values in hist.instrumentName:
            new_column.append(re.search(r'\w{3}\/\w{3}', values).group().replace("/", ""))

        hist['name'] = new_column

        hist['profitAndLoss'] = hist.profitAndLoss.str.replace("E", "").astype(float)

        return hist


    def report_last_day(self,ti,dp_service):
        start_time = (datetime.now() - timedelta(hours=24))
        start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%S")

        hist = self.get_transaction_history(start_time)
        if len(hist) == 0:
            return

        hist = hist.set_index("openDateUtc")
        hist.sort_index(inplace=True)
        hist.reset_index(inplace=True)

        #hist['profitAndLoss'] = hist['profitAndLoss'].str.replace('E', '', regex=True).astype('float64')
        hist["openDateUtc"] = pd.to_datetime(hist["openDateUtc"])
        hist["dateUtc"] = pd.to_datetime(hist["dateUtc"])
        hist["openLevel"] = hist["openLevel"].astype("float")
        hist["closeLevel"] = hist["closeLevel"].astype("float")

        hist = self.fix_hist(hist)

        for ticker in hist['name'].unique():

            df = ti.load_data_by_date(ticker, start_time.strftime("%Y-%m-%d"),
                                      None, DataProcessor(), "1min", False, False)
            if len(df) == 0:
                continue

            df = df[df["date"] > start_time_str]

            temp_hist = hist[hist['name'] == ticker]

            df = df.filter(["close", "date"])

            winner = temp_hist[temp_hist["profitAndLoss"] >= 0]
            looser = temp_hist[temp_hist["profitAndLoss"] < 0]

            long_winner = winner[winner["closeLevel"] >= winner["openLevel"]]
            short_winner = winner[winner["closeLevel"] <= winner["openLevel"]]

            long_looser = looser[looser["closeLevel"] < looser["openLevel"]]
            short_looser = looser[looser["closeLevel"] > looser["openLevel"]]

            shorts = short_winner.append(short_looser)
            longs = long_winner.append(long_looser)

            plt.figure(figsize=(15, 6))
            plt.cla()
            chart, = plt.plot(pd.to_datetime(df["date"]), df["close"], color='#d3d3d3', alpha=0.5, label=ticker)
            for i in range(len(shorts)):
                row = shorts[i:i + 1]
                pl = row.openLevel - row.closeLevel

                stopLine, = plt.plot([row.openDateUtc, row.dateUtc], [row.openLevel - pl, row.openLevel - pl],
                                     color="#ff0000")
                limitLine, = plt.plot([row.openDateUtc, row.dateUtc], [row.openLevel + pl, row.openLevel + pl],
                                      color="#00ff00", label="Limit")

            for i in range(len(longs)):
                row = longs[i:i + 1]
                pl = row.closeLevel - row.openLevel

                plt.plot([row.openDateUtc, row.dateUtc], [row.openLevel + pl, row.openLevel + pl], color="#ff0000")
                plt.plot([row.openDateUtc, row.dateUtc], [row.openLevel - pl, row.openLevel - pl], color="#00ff00")

            # long open
            buy, = plt.plot(long_winner["openDateUtc"], long_winner["openLevel"], 'b^', label="Buy")
            plt.plot(long_looser["openDateUtc"], long_looser["openLevel"], 'b^')

            # short open
            sell, = plt.plot(short_winner["openDateUtc"], short_winner["openLevel"], 'bv', label="Sell")
            plt.plot(short_looser["openDateUtc"], short_looser["openLevel"], 'bv')

            # long close
            profit, = plt.plot(long_winner["dateUtc"], long_winner["closeLevel"], 'go', label="Profit")
            loss, = plt.plot(long_looser["dateUtc"], long_looser["closeLevel"], 'rx', label="Loss")

            # short close
            plt.plot(short_winner["dateUtc"], short_winner["closeLevel"], 'go')
            plt.plot(short_looser["dateUtc"], short_looser["closeLevel"], 'rx')

            hours = self._get_hours(temp_hist[0:1])
            for h in hours:
                plt.axvline(x=h, color='b', label='axvline - full height', alpha=0.1)

            # plot legend
            # plt.legend(handles=[stopLine, limitLine, chart, buy, sell, profit, loss])
            plt.suptitle(
                f"{ticker} - Summary of last 24 hours: Profit {hist['profitAndLoss'].sum()} Won: {len(winner)} Lost: {len(looser)}")

            tempng = os.path.join(tempfile.gettempdir(), f"{ticker}.png")
            plt.savefig(tempng)

            dp_service.upload(tempng,
                              os.path.join(
                                  datetime.now().strftime("%Y_%m_%d"),
                                  f"{ticker}.png"))

    def report_summary(self, ti, dp_service,delta:timedelta=timedelta(hours=24),name:str="lastday"):
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

        dp_service.upload(temp_file,
                          os.path.join(
                              datetime.now().strftime("%Y_%m_%d"),
                              f"summary_{name}.md"))

        return

    def create_report(self, ti,dp_service):
        self.report_summary(ti,dp_service,timedelta(hours=24),"lastday")
        self.report_summary(ti, dp_service, timedelta(days=7), "lastweek")
        self.report_last_day(ti,dp_service)

