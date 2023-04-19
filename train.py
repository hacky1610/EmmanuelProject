from Connectors.IG import IG
from Connectors.tiingo import TradeType,Tiingo
from Predictors.trainer import Trainer
from BL.utils import ConfigReader
from BL.data_processor import DataProcessor
from BL.analytics import Analytics
import os
import tempfile
from datetime import datetime
from Connectors.dropboxservice import DropBoxService
import dropbox

dbx = dropbox.Dropbox(ConfigReader().get("dropbox"))
ds = DropBoxService(dbx, "DEMO")
temp_file = os.path.join(tempfile.gettempdir(), f"evaluate.xlsx")
trainer = Trainer(Analytics())
conf_reader = ConfigReader()
tiingo = Tiingo(conf_reader=conf_reader)
dp = DataProcessor()


markets = IG(conf_reader=conf_reader).get_markets(tradeable=False,trade_type=TradeType.FX)
for m in markets:
    symbol = m["symbol"]
    #symbol = "EURSGD"
    df,eval = tiingo.load_live_data(symbol,dp,TradeType.FX)
    if len(df) > 0:
        res = trainer.train_RSI_STOCH(symbol,df,eval)
        if len(res) > 0:
            try:
                res.to_excel(temp_file)
                t = datetime.now().strftime("%Y_%m_%d_%H:%M:%S")
                ds.upload(temp_file, os.path.join("Training_RSI_STOCH_Linux", f"{t}_{symbol}.xlsx"))
            except:
                print("Error")
    else:
        print(f"No Data in {symbol} ")








