# region import
import random
import traceback

from BL import DataProcessor, ConfigReader
from BL.analytics import Analytics
from BL.eval_result import EvalResultCollection
from Connectors.IG import IG
from Connectors.dropbox_cache import DropBoxCache
from Connectors.dropboxservice import DropBoxService
from Connectors.market_store import MarketStore
from Connectors.tiingo import Tiingo, TradeType
from UI.base_viewer import BaseViewer
import dropbox
import pymongo

# endregion

# region static members
conf_reader = ConfigReader()
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx, "DEMO")
df_cache = DropBoxCache(ds)
dp = DataProcessor()
_ig = IG(conf_reader)
_ti = Tiingo(conf_reader=conf_reader, cache=df_cache)
client = pymongo.MongoClient(f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ms = MarketStore(db)
analytics = Analytics(ms,_ig)
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
        try:
            ti.init_data(symbol, trade_type, days=250)
        except Exception as e:
            traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
            print(f"MainException: {e} File:{traceback_str}")


# endregion

init_data(_ig, _ti)
