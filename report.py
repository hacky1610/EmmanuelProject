from BL import DataProcessor
from BL.analytics import Analytics
from BL.indicators import Indicators
from Connectors.IG import IG
from Connectors.dropbox_cache import DropBoxCache
from Connectors.tiingo import Tiingo
from BL.utils import ConfigReader
import dropbox
from Connectors.dropboxservice import DropBoxService
from Predictors.chart_pattern_rectangle import RectanglePredictor
from Predictors.generic_predictor import GenericPredictor

conf_reader = ConfigReader()
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx,"DEMO")
cache = DropBoxCache(ds)
tiingo = Tiingo(conf_reader=conf_reader, cache=cache)
ig = IG(conf_reader=conf_reader)
predictor = GenericPredictor(indicators=Indicators())

ig.create_report(ti=tiingo,
                 dp_service=ds,
                 predictor=predictor,
                 cache=cache,
                 dp=DataProcessor(),
                 analytics=Analytics())
