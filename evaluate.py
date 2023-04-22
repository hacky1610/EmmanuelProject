from BL.data_processor import DataProcessor
from Connectors.tiingo import Tiingo, TradeType
from Predictors import *
from Predictors.rsi_stoch import RsiStoch
from Predictors.rsi_bb import RsiBB

from BL.utils import ConfigReader
from Connectors.IG import IG
from BL import Analytics

# Prep
conf_reader = ConfigReader()
dp = DataProcessor()
ig = IG(conf_reader)
ti = Tiingo(conf_reader=conf_reader)
analytics = Analytics()

for m in ig.get_markets(tradeable=False, trade_type=TradeType.FX):
    symbol = m["symbol"]
    #symbol = "CADCHF"
    df, df_eval = ti.load_live_data(symbol,dp, TradeType.FX)

    if len(df) > 0:
        predictor = RsiBB()
        predictor.load(symbol)
        reward, success, trade_freq, win_loss, avg_minutes = analytics.evaluate(predictor, df, df_eval, False)
        max_spread = success * m["scaling"] * 0.2
        print(f"{symbol} - Reward {reward}, success {success}, trade_freq {trade_freq}, win_loss {win_loss} avg_minutes {avg_minutes} spread {max_spread}")
