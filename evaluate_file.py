from BL import DataProcessor, Analytics, ConfigReader
from Connectors import Tiingo, TradeType, IG, DropBoxCache, DropBoxService, BaseCache
from Predictors.old.sup_res_candle import SupResCandle
from UI.plotly_viewer import PlotlyViewer

import dropbox
import pandas as pd

# Prep
conf_reader = ConfigReader()
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx,"DEMO")
cache = DropBoxCache(ds)
dp = DataProcessor()
ig = IG(conf_reader)





ti = Tiingo(conf_reader=conf_reader,cache=BaseCache())
analytics = Analytics()
trade_type = TradeType.FX

viewer = PlotlyViewer()

symbol = "AUDCHF"
df_file = pd.read_csv("C:\\Users\\adhada7\\Downloads\\AUDCHF_FECAPUBBFAWTY2F.csv")

df_online, df_eval = ti.load_train_data(symbol, dp, trade_type)

predictor = SupResCandle()
predictor.load(symbol)
action = predictor.predict(df_file)
print(f"{action}")


