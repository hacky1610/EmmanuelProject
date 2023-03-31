from trading_ig import IGService
from trading_ig.rest import IGException
from pandas import DataFrame
from Data.data_processor import DataProcessor
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.Tracer import Tracer
from LSTM_Logic import Utils
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta


class IG:

    def __init__(self, tracer: Tracer = ConsoleTracer()):
        c = Utils.read_config()
        self.user = c["ig_demo_user"]
        self.password = c["ig_demo_pass"]
        self.key = c["ig_demo_key"]
        self.accNr = c["ig_demo_acc_nr"]
        self.type = "DEMO"
        self._tracer: Tracer = tracer
        self.connect()

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
            res = self.ig_service.fetch_market_by_epic(epic)
            return (res["snapshot"]['offer'] - res["snapshot"]['bid']) * 10000
        except IGException as ex:
            self._tracer.error(f"Error during open a position. {ex}")
            return None

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

    def buy(self, epic: str):
        return self.open(epic, "BUY")

    def sell(self, epic: str):
        return self.open(epic, "SELL")

    def open(self, epic: str, direction: str) -> bool:
        try:
            response = self.ig_service.create_open_position(
                currency_code="USD",
                direction=direction,
                epic=epic,
                expiry="-",
                force_open=True,
                guaranteed_stop=True,
                order_type="MARKET",
                size=1,
                level=None,
                limit_distance=9,
                limit_level=None,
                quote_id=None,
                stop_distance=27,
                stop_level=None,
                trailing_stop=False,
                trailing_stop_increment=None
            )
            if response["dealStatus"] != "ACCEPTED":
                self._tracer.error(f"could not open trade: {response['reason']}")
                return False
            return True
        except IGException as ex:
            self._tracer.error(f"Error during open a position. {ex}")
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
        return self.ig_service.fetch_transaction_history(trans_type="ALL", from_date=start_time,
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


    def create_report(self, df: DataFrame, symbol_name: str, start_time:str):
        limit = 0.0009
        stopp = 0.0018
        hist = self.get_transaction_history(start_time)
        hist = hist.set_index("openDateUtc")
        hist = hist[hist["transactionType"] == "TRADE"]
        hist.sort_index(inplace=True)
        hist.reset_index(inplace=True)
        hist['profitAndLoss'] = hist['profitAndLoss'].str.replace('E', '', regex=True).astype('float64')
        hist["openDateUtc"] = pd.to_datetime(hist["openDateUtc"])
        hist["dateUtc"] = pd.to_datetime(hist["dateUtc"])
        hist["openLevel"] = hist["openLevel"].astype("float")
        hist["closeLevel"] = hist["closeLevel"].astype("float")

        df = df.filter(["close", "date"])

        winner = hist[hist["profitAndLoss"] >= 0]
        looser = hist[hist["profitAndLoss"] < 0]

        long_winner = winner[winner["closeLevel"] >= winner["openLevel"]]
        short_winner = winner[winner["closeLevel"] <= winner["openLevel"]]

        long_looser = looser[looser["closeLevel"] < looser["openLevel"]]
        short_looser = looser[looser["closeLevel"] > looser["openLevel"]]

        shorts = short_winner.append(short_looser)
        longs = long_winner.append(long_looser)

        plt.figure(figsize=(15, 6))
        plt.cla()
        chart, = plt.plot(pd.to_datetime(df["date"]), df["close"], color='#d3d3d3', alpha=0.5, label=symbol_name)

        for i in range(len(shorts)):
            row = shorts[i:i + 1]
            stopLine, = plt.plot([row.openDateUtc, row.dateUtc], [row.openLevel - limit, row.openLevel - limit],
                                 color="#00ff00")
            limitLine, = plt.plot([row.openDateUtc, row.dateUtc], [row.openLevel + stopp, row.openLevel + stopp],
                                  color="#ff0000", label="Limit")

        for i in range(len(longs)):
            row = longs[i:i + 1]
            plt.plot([row.openDateUtc, row.dateUtc], [row.openLevel + limit, row.openLevel + limit], color="#00ff00")
            plt.plot([row.openDateUtc, row.dateUtc], [row.openLevel - stopp, row.openLevel - stopp], color="#ff0000")

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

        hours = self._get_hours(hist[0:1])
        for h in hours:
            plt.axvline(x=h, color='b', label='axvline - full height', alpha=0.1)

        #plot legend
        plt.legend(handles=[stopLine, limitLine, chart, buy, sell, profit, loss])
        plt.suptitle(
            f"Summary of last 24 hours: Profit {hist['profitAndLoss'].sum()} Won: {len(winner)} Lost: {len(looser)}")
        plt.show(block=True)
        return
