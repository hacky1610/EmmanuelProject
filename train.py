from multiprocessing import Process
import random

from Connectors.IG import IG
from Connectors.dropbox_cache import DropBoxCache
from Connectors.tiingo import TradeType, Tiingo
from Predictors.trainer import Trainer
from BL.utils import ConfigReader
from BL.data_processor import DataProcessor
from BL.analytics import Analytics
import os
from Connectors.dropboxservice import DropBoxService
import dropbox

conf_reader = ConfigReader()
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx, "DEMO")
cache = DropBoxCache(ds)
trainer = Trainer(Analytics(),cache=cache)
tiingo = Tiingo(conf_reader=conf_reader,cache=cache)
dp = DataProcessor()
trade_type = TradeType.FX
ig = IG(conf_reader=conf_reader)
train_version = "V2.18"
loop = True


while True:
    markets = ig.get_markets(tradeable=False, trade_type=trade_type)
    #for m in random.choices(markets,k=30):
    for m in markets:
        symbol = m["symbol"]
        #symbol = "AUDUSD"
        if trainer.is_trained(symbol, train_version) and not loop:
            print(f"{symbol} Already trained with version {train_version}.")
            continue
        df, eval = tiingo.load_train_data(symbol, dp, trade_type=trade_type)
        if len(df) > 0:
            if os.name == "nt":
                trainer.train(symbol, df, eval, train_version)
            else:
                p = Process(target=trainer.train,args=(symbol,df, eval, train_version))
                p.start()
        else:
            print(f"No Data in {symbol} ")
