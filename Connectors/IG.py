from trading_ig import IGService
from trading_ig.rest import IGException
from pandas import DataFrame
from Data.data_processor import DataProcessor
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.Tracer import Tracer


class IG:

    def __init__(self, tracer: Tracer = ConsoleTracer()):
        c = Logic.Utils.read_config()
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
