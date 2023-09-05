# region import
import random
from BL import DataProcessor, Analytics, ConfigReader
from BL.eval_result import  EvalResultCollection
from Connectors import Tiingo, TradeType, DropBoxCache, DropBoxService
from Connectors.IG import IG
from UI.base_viewer import BaseViewer
import dropbox

# endregion

# region static members
conf_reader = ConfigReader()
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx, "DEMO")
df_cache = DropBoxCache(ds)
dp = DataProcessor()
ig = IG(conf_reader)
ti = Tiingo(conf_reader=conf_reader, cache=df_cache)
analytics = Analytics()
trade_type = TradeType.FX
results = EvalResultCollection()
viewer = BaseViewer()
only_one_position = False


# endregion

# region functions
def init_data(ig: IG, ti: Tiingo):
    global symbol
    markets = ig.get_markets(tradeable=False, trade_type=trade_type)
    for m in markets:
        symbol = m["symbol"]
        #symbol = "AUDJPY"
        ti.init_data(symbol, trade_type)


# endregion

init_data(ig, ti)