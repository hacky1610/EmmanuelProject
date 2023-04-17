from BL.data_processor import DataProcessor
from Connectors.tiingo import Tiingo, TradeType
from Predictors import *
import pandas as pd
from BL.utils import ConfigReader,load_train_data
from Connectors.IG import IG

# Prep
dp = DataProcessor()
ig = IG(ConfigReader())
ti = Tiingo(conf_reader=ConfigReader())


for m in ig.get_markets(tradeable=False,trade_type=TradeType.FX ):
    symbol = m["symbol"]
    #symbol = "btcusd"
    #load_train_data(symbol,ti,dp)

    try:
        df = pd.read_csv(f"./Data/{symbol}_1hour.csv", delimiter=",")
        df_eval = pd.read_csv(f"./Data/{symbol}_5min.csv", delimiter=",")
        df_eval.drop(columns=["level_0"], inplace=True)
        predictor = RsiStoch({})
        predictor.set_config(symbol)
        reward, success, trade_freq, win_loss, avg_minutes  = evaluate(predictor, df, df_eval, False)

        print(f"{symbol} - Reward {reward}, success {reward}, trade_freq {trade_freq}, win_loss {win_loss} avg_minutes {avg_minutes}")
    except Exception:
        print(f"{symbol} missing")




