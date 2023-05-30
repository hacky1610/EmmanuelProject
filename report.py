from Connectors import DropBoxCache
from Connectors.IG import IG
from Connectors.tiingo import Tiingo
from BL.utils import ConfigReader
import dropbox
from Predictors.sup_res_candle import SupResCandle
from Connectors.dropboxservice import DropBoxService


conf_reader = ConfigReader()
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx,"DEMO")
cache = DropBoxCache(ds)
tiingo = Tiingo(conf_reader=conf_reader, cache=cache)
ig = IG(conf_reader=conf_reader)
predictor = SupResCandle()

ig.create_report(tiingo,ds,predictor)
