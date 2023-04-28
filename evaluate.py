from BL.data_processor import DataProcessor
from Connectors.tiingo import Tiingo, TradeType
from Predictors.rsi_bb import RsiBB
from BL.utils import ConfigReader
from Connectors.IG import IG
from BL import Analytics
import time

# Prep
conf_reader = ConfigReader()
dp = DataProcessor()
ig = IG(conf_reader)
ti = Tiingo(conf_reader=conf_reader)
analytics = Analytics()
trade_type = TradeType.FX

while True:
    df = ti.load_live_data_last_days("GBPUSD", dp, trade_type)
    d = df[df.date < "2023-04-28T12:00:00.001Z"]
    print(d[-2:].filter(["date","close","high","low","open"]))
    time.sleep(60 * 10)

for m in ig.get_markets(tradeable=False, trade_type=trade_type):
    symbol = m["symbol"]
    symbol = "GBPUSD"

    if len(df) > 0:
        predictor = RsiBB()
        predictor.load(symbol)
        r = predictor.predict(df)
        reward, success, trade_freq, win_loss, avg_minutes = analytics.evaluate(predictor, df, df_eval, True)
        max_spread = success * m["scaling"] * 0.2
        print(f"{symbol} - Reward {reward}, success {success}, trade_freq {trade_freq}, win_loss {win_loss} avg_minutes {avg_minutes} spread {max_spread}")
