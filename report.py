from Connectors.IG import IG
from Connectors.tiingo import Tiingo
from datetime import date, timedelta
from Data.data_processor import DataProcessor

symbol = "GBPUSD"
tiingo = Tiingo()
ig = IG()
start_day = (date.today() - timedelta(hours=24))

df = tiingo.load_data_by_date(symbol, start_day.strftime("%Y-%m-%d"),
                              None, DataProcessor(), "1min")
ig.create_report(df, symbol, start_day.strftime("%Y-%m-%dT%H:%M:%S"))
