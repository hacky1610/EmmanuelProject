from Connectors.IG import IG
from Connectors.tiingo import Tiingo
from datetime import date, timedelta
from Data.data_processor import DataProcessor

symbol = "GBPUSD"
tiingo = Tiingo()
ig = IG()

df =  tiingo.load_data_by_date(symbol, (date.today() - timedelta(hours=30)).strftime("%Y-%m-%d"),
                                                  None, DataProcessor(),"1min")
ig.create_report(df,symbol)