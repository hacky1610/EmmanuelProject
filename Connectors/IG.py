from trading_ig import IGService
import Utils.Utils
from pandas import DataFrame
from Data.data_processor import DataProcessor

class IG:

    def __init__(self):
        c = Utils.Utils.read_config()
        self.user = c["ig_demo_user"]
        self.password = c["ig_demo_pass"]
        self.key = c["ig_demo_key"]
        self.accNr = c["ig_demo_acc_nr"]
        self.type = "DEMO"
        self.connect()

    def connect(self):
        # no cache
        self.ig_service = IGService(
            self.user, self.password, self.key, self.type, acc_number=self.accNr
        )
        self.ig_service.create_session()

    def create_dataframe(self,ig_dataframe,data_processor:DataProcessor):
        df = DataFrame()
        df["Open"] = ig_dataframe["bid", "Open"]
        df["Low"] = ig_dataframe["bid", "Low"]
        df["High"] = ig_dataframe["bid", "High"]
        df["Close"] = ig_dataframe["bid", "Close"]
        df["Volume"] = ig_dataframe["last", "Volume"]

        data_processor.addSignals(df)
        data_processor.clean_data(df)
        return df

    def load_data_by_date(self, epic:str, start:str, end:str, data_processor:DataProcessor, resolution:str= "H"):
        resolution = "H"
        response = self.ig_service.fetch_historical_prices_by_epic_and_date_range(
            epic, resolution, start,end
        )
        ig_df = response["prices"]
        return self.create_dataframe(ig_df,data_processor)

    def load_data_by_range(self, epic:str, range, data_processor:DataProcessor, resolution:str= "H"):
        resolution = "H"
        response = self.ig_service.fetch_historical_prices_by_epic(
            epic, resolution, numpoints=range
        )
        ig_df = response["prices"]
        return self.create_dataframe(ig_df,data_processor)

    def buy(self,epic:str):
        response = self.ig_service.create_open_position(
            currency_code="USD",
            direction="BUY",
            epic=epic,
            expiry="-",
            force_open=False,
            guaranteed_stop=False,
            order_type="MARKET",
            size=1,
            level=None,
            limit_distance=None,
            limit_level=None,
            quote_id=None,
            stop_distance=None,
            stop_level=None,
            trailing_stop=False,
            trailing_stop_increment=None
        )

    def has_opened_positions(self):
        positions =  self.ig_service.fetch_open_positions()
        return len(positions) > 0

    def get_opened_position_id(self):
        positions = self.ig_service.fetch_open_positions()
        return positions["dealId"][0]

    def sell(self,deal_id:str):
        response = self.ig_service.close_open_position(
            deal_id=deal_id,
            direction="SELL",
            epic=None,
            expiry="-",
            order_type="MARKET",
            size=1,
            level=None,
            quote_id=None
        )









