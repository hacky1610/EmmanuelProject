from Data.data_processor import DataProcessor
from Connectors.tiingo import Tiingo
from Predictors import CCI,RSI
import pandas as pd


#ray.init(local_mode=True)

# Prep
dp = DataProcessor()
ti = Tiingo()
df = ti.load_data_by_date("GBPUSD","2023-01-02","2023-02-28",dp)
df_eval = pd.read_csv("./Data/GBPUSD.csv")

#print(rsi.evaluate(df,df_eval))
#print(cci.evaluate(df,df_eval))

upper_limit = range(80,120)
lower_limit = range(-140,-90)
stop_limit = [.0007,.0009,.0013,.0017]

best = 0


for ul in upper_limit:
    for ll in lower_limit:
        for stop in stop_limit:
            for limit in stop_limit:
                rsi = CCI({"lower_limit":ll, "upper_limit":ul,"df":df,"df_eval":df_eval, "stop":stop,"limit":limit})
                res = rsi.step()

                if res["success"] > best:
                    best = res["success"]
                    reward = res["reward"]
                    frequ = res["trade_frequency"]
                    w_l = res["win_loss"]
                    print(f"Best: low {ll} high {ul}  limit {limit} stop {stop} - Avg Reward: {best} Max reward: {reward}  Freq: {frequ} WinLoss: {w_l}" )


