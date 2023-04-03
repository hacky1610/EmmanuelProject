from Data.data_processor import DataProcessor
from Connectors.tiingo import Tiingo
from Predictors import *
import pandas as pd

# Prep
dp = DataProcessor()
ti = Tiingo()
df = ti.load_data_by_date("gbpusd","2023-01-02","2023-02-28",dp)
df_eval = pd.read_csv("./Data/GBPUSD.csv")

print(evaluate(RSI({}),df,df_eval))
#print(rsi.evaluate(df,df_eval))
#print(cci.evaluate(df,df_eval))

upper_limit = range(90,110,5)
lower_limit = range(-110,-90,5)
stop_limit = [.0007,.0009,.0013,.0017,.0029,.0043,.0057]
best = 0

for ul in upper_limit:
    for ll in lower_limit:
        for stop in stop_limit:
            for limit in stop_limit:
                rsi = CCI_EMA({"lower_limit":ll, "upper_limit":ul,"df":df,"df_eval":df_eval, "stop":stop,"limit":limit})
                res = rsi.step()

                if res["success"] > best:
                    best = res["success"]
                    reward = res["reward"]
                    frequ = res["trade_frequency"]
                    w_l = res["win_loss"]
                    print(f"Best: low {ll} high {ul}  limit {limit} stop {stop} - Avg Reward: {best} Max reward: {reward}  Freq: {frequ} WinLoss: {w_l}" )


