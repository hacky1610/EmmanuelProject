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
rsi = RSI({})
cci = CCI({})

#print(rsi.evaluate(df,df_eval))
#print(cci.evaluate(df,df_eval))

upper_limit = range(5,120)
lower_limit = range(-120,-5)

best = 0


for ul in upper_limit:
    for ll in lower_limit:
        rsi = CCI({"lower_limit":ll, "upper_limit":ul,"df":df,"df_eval":df_eval})
        res = rsi.step()

        if res["success"] > best:
            best = res["success"]
            print(f"Best: {ll} {ul} - {best}" )


