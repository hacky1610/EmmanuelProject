from Connectors.IG import IG
from Connectors.tiingo import Tiingo
from datetime import date, timedelta, datetime
from Data.data_processor import DataProcessor
from Logic.analytics import Analytics

symbol = "GBPUSD"
tiingo = Tiingo()
ig = IG()
start_time = (datetime.now() - timedelta(hours=24))
start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%S")

df = tiingo.load_data_by_date(symbol, start_time.strftime("%Y-%m-%d"),
                              None, DataProcessor(), "1hour",False,False)

a = Analytics()
a.has_peak(df)

ig.create_report(df[df["date"] > start_time_str], symbol, start_time_str)
