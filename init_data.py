# region import
import random
from BL import DataProcessor, Analytics, ConfigReader
from BL.eval_result import EvalResultCollection
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
_ig = IG(conf_reader)
_ti = Tiingo(conf_reader=conf_reader, cache=df_cache)
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
        #symbol = "AUDUSD"
        try:
            ti.init_data(symbol, trade_type, days=250)
        except Exception as e:
            print(e)


# endregion

init_data(_ig, _ti)
