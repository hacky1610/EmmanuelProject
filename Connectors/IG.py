from trading_ig import IGService
from trading_ig.rest import IGException
from pandas import DataFrame
from Data.data_processor import DataProcessor
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.Tracer import Tracer
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta
import re
from BL.utils import *


class IG:

    def __init__(self, tracer: Tracer = ConsoleTracer(),stock_list = []):
        c = read_config()
        self.user = c["ig_demo_user"]
        self.password = c["ig_demo_pass"]
        self.key = c["ig_demo_key"]
        self.accNr = c["ig_demo_acc_nr"]
        self.type = "DEMO"
        self._tracer: Tracer = tracer
        self._stock_list = stock_list
        self.connect()

    def _get_symbol(self,symbol:str) -> str:
        if len(self._stock_list) == 0:
            return  symbol


        return self._stock_list.IG[symbol]

    def get_markets(self):
        market_df = self.ig_service.search_markets("CURRENCIES")
        markets = []
        market_df =  market_df[market_df.marketStatus == "TRADEABLE"]
        market_df =market_df[~market_df["instrumentName"].str.contains("Mini")]
        for market in market_df.iterrows():
            markets.append({
                "symbol":market[1].instrumentName.replace("/","").replace(" Kassa",""),
                "epic":market[1].epic,
                "spread": (market[1].offer - market[1].bid) * market[1].scalingFactor,
                "scaling": market[1].scalingFactor
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

    def get_spread(self, epic: str):
        try:
            res = self.ig_service.fetch_market_by_epic(self._get_symbol(epic))
            return (res["snapshot"]['offer'] - res["snapshot"]['bid']) * res["snapshot"]["scalingFactor"]
        except IGException as ex:
            self._tracer.error(f"Error fetching infos for {epic} {ex} ")
            return 1000
        except Exception as ex:
            self._tracer.error(f"Error fetching infos for {epic} {ex} ")
            return 1000

    def create_dataframe(self, ig_dataframe, data_processor: DataProcessor):
        df = DataFrame()
        df["Open"] = ig_dataframe["bid", "Open"]
        df["Low"] = ig_dataframe["bid", "Low"]
        df["High"] = ig_dataframe["bid", "High"]
        df["Close"] = ig_dataframe["bid", "Close"]
        df["Volume"] = ig_dataframe["last", "Volume"]

        data_processor.addSignals(df)
        data_processor.clean_data(df)
        return df

    def buy(self, epic: str, stop:int,limit:int):
        return self.open(epic, "BUY",stop,limit)

    def sell(self, epic: str,stop:int,limit:int):
        return self.open(epic, "SELL",stop,limit)

    def open(self, epic: str, direction: str, stop:int = 25, limit:int = 25) -> bool:
        try:
            response = self.ig_service.create_open_position(
                currency_code=epic[-10:-7],
                direction=direction,
                epic=epic,
                expiry="-",
                force_open=True,
                guaranteed_stop=False,
                order_type="MARKET",
                size=1,
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

    def get_transaction_history(self, start_time:str):
        return self.ig_service.fetch_transaction_history(trans_type="ALL_DEAL", from_date=start_time,
                                                         max_span_seconds=60 * 50)

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


    def create_report(self,ti):
        start_time = (datetime.now() - timedelta(hours=24))
        start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%S")

        hist = self.get_transaction_history(start_time)
        hist = hist.set_index("openDateUtc")
        hist.sort_index(inplace=True)
        hist.reset_index(inplace=True)

        hist['profitAndLoss'] = hist['profitAndLoss'].str.replace('E', '', regex=True).astype('float64')
        hist["openDateUtc"] = pd.to_datetime(hist["openDateUtc"])
        hist["dateUtc"] = pd.to_datetime(hist["dateUtc"])
        hist["openLevel"] = hist["openLevel"].astype("float")
        hist["closeLevel"] = hist["closeLevel"].astype("float")

        new_column = []
        for values in hist.instrumentName:
            new_column.append(re.search(r'\w{3}\/\w{3}', values).group().replace("/",""))

        hist['name'] = new_column

        for ticker in hist['name'].unique():


            df = ti.load_data_by_date(ticker, start_time.strftime("%Y-%m-%d"),
                                          None, DataProcessor(), "1min", False, False)
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
                                     color="#00ff00")
                limitLine, = plt.plot([row.openDateUtc, row.dateUtc], [row.openLevel + pl, row.openLevel + pl],
                                      color="#ff0000", label="Limit")

            for i in range(len(longs)):
                row = longs[i:i + 1]
                pl = row.closeLevel - row.openLevel

                plt.plot([row.openDateUtc, row.dateUtc], [row.openLevel + pl, row.openLevel + pl], color="#00ff00")
                plt.plot([row.openDateUtc, row.dateUtc], [row.openLevel - pl, row.openLevel - pl], color="#ff0000")

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

            #plot legend
            #plt.legend(handles=[stopLine, limitLine, chart, buy, sell, profit, loss])
            plt.suptitle(
                f"{ticker} - Summary of last 24 hours: Profit {hist['profitAndLoss'].sum()} Won: {len(winner)} Lost: {len(looser)}")
            plt.show(block=True)
        return
