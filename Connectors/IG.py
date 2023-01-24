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
    def load_data(self,epic:str,start:str,end:str,data_processor:DataProcessor, resolution:str="H"):

        # no cache
        ig_service = IGService(
            self.user, self.password ,  self.key , self.type, acc_number=self.accNr
        )
        ig_service.create_session()
        resolution = "H"
        response = ig_service.fetch_historical_prices_by_epic_and_date_range(
            epic, resolution, start,end
        )
        ig_df = response["prices"]


        df = DataFrame()
        df["Open"] = ig_df["bid","Open"]
        df["Low"] = ig_df["bid","Low"]
        df["High"] = ig_df["bid","High"]
        df["Close"] = ig_df["bid","Close"]
        df["Volume"] = ig_df["last", "Volume"]

        data_processor.addSignals(df)

        print(df)




