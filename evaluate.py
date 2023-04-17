from BL.data_processor import DataProcessor
from Connectors.tiingo import Tiingo, TradeType
from Predictors import *
from BL.utils import ConfigReader
from Connectors.IG import IG

# Prep
conf_reader = ConfigReader()
dp = DataProcessor()
ig = IG(conf_reader)
ti = Tiingo(conf_reader=conf_reader)

for m in ig.get_markets(tradeable=False, trade_type=TradeType.FX):
    symbol = m["symbol"]
    # symbol = "GBPUSD"
    df, df_eval = ti.load_live_data(symbol,dp, TradeType.FX)

    predictor = RsiStoch({})
    predictor.set_config(symbol)
    reward, success, trade_freq, win_loss, avg_minutes = evaluate(predictor, df, df_eval, True)

    print(
        f"{symbol} - Reward {reward}, success {reward}, trade_freq {trade_freq}, win_loss {win_loss} avg_minutes {avg_minutes}")
