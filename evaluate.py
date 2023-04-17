from BL.data_processor import DataProcessor
from Connectors.tiingo import Tiingo, TradeType
from Predictors import *
import pandas as pd
from BL.utils import ConfigReader, load_train_data, load_live_data
from Connectors.IG import IG

# Prep
dp = DataProcessor()
ig = IG(ConfigReader())
ti = Tiingo(conf_reader=ConfigReader())

for m in ig.get_markets(tradeable=False, trade_type=TradeType.FX):
    symbol = m["symbol"]
    # symbol = "GBPUSD"
    df, df_eval = load_live_data(symbol, ti, dp, TradeType.FX)

    predictor = RsiStoch({})
    predictor.set_config(symbol)
    reward, success, trade_freq, win_loss, avg_minutes = evaluate(predictor, df, df_eval, True)

    print(
        f"{symbol} - Reward {reward}, success {reward}, trade_freq {trade_freq}, win_loss {win_loss} avg_minutes {avg_minutes}")
