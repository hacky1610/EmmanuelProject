from Data.data_processor import DataProcessor
from Connectors.tiingo import Tiingo
from Predictors import *
import pandas as pd
from BL.utils import ConfigReader,load_train_data
from Connectors.IG import IG

# Prep
dp = DataProcessor()
ig = IG(ConfigReader())
ti = Tiingo(conf_reader=ConfigReader())

for m in ig.get_markets(tradebale=False):
    symbol = m["symbol"]

    try:
        df = pd.read_csv(f"./Data/{symbol}_1hour.csv", delimiter=",")
        df_eval = pd.read_csv(f"./Data/{symbol}_5min.csv", delimiter=",")
        df_eval.drop(columns=["level_0"], inplace=True)
        reward, success, trade_freq, win_loss  = evaluate(CCI_EMA({"df": df, "df_eval": df_eval}), df, df_eval)

        print(f"{symbol} - Reward {reward}, success {reward}, trade_freq {trade_freq}, win_loss {win_loss}")
    except Exception:
        print(f"{symbol} missing")



