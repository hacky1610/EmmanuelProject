#region import
from multiprocessing import Process
from Connectors.IG import IG
from Connectors.dropbox_cache import DropBoxCache
from Connectors.tiingo import TradeType, Tiingo
from Predictors.chart_pattern_rectangle import RectanglePredictor
from Predictors.chart_pattern_triangle import TrianglePredictor
from Predictors.trainer import Trainer
from BL.utils import ConfigReader
from BL.data_processor import DataProcessor
from BL.analytics import Analytics
import os
from Connectors.dropboxservice import DropBoxService
import dropbox
#endregions

#region statics
conf_reader = ConfigReader()
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx, "DEMO")
cache = DropBoxCache(ds)
trainer = Trainer(Analytics(),cache=cache)
tiingo = Tiingo(conf_reader=conf_reader,cache=cache)
dp = DataProcessor()
trade_type = TradeType.FX
ig = IG(conf_reader=conf_reader)
#endregion


train_version = "V2.18"
loop = True
predictor = TrianglePredictor
predictor = RectanglePredictor


while True:
    markets = ig.get_markets(tradeable=False, trade_type=trade_type)
    #for m in random.choices(markets,k=30):
    for m in markets:
        symbol = m["symbol"]
        #symbol = "AUDUSD"
        if trainer.is_trained(symbol, train_version,predictor) and not loop:
            print(f"{symbol} Already trained with version {train_version}.")
            continue
        df, eval = tiingo.load_train_data(symbol, dp, trade_type=trade_type)
        if len(df) > 0:
            if os.name == "nt":
                trainer.train(symbol, df, eval, train_version, predictor)
            else:
                p = Process(target=trainer.train,args=(symbol,df, eval, train_version))
                p.start()
        else:
            print(f"No Data in {symbol} ")
