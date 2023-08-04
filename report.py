from Connectors import DropBoxCache
from Connectors.IG import IG
from Connectors.tiingo import Tiingo
from BL.utils import ConfigReader
import dropbox
from Connectors.dropboxservice import DropBoxService
from Predictors.chart_pattern_rectangle import RectanglePredictor

conf_reader = ConfigReader()
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx,"DEMO")
cache = DropBoxCache(ds)
tiingo = Tiingo(conf_reader=conf_reader, cache=cache)
ig = IG(conf_reader=conf_reader)
predictor = RectanglePredictor()

ig.create_report(ti=tiingo,
                 dp_service=ds,
                 predictor=predictor,
                 cache=cache)
