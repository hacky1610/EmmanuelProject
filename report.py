from BL import DataProcessor
from BL.analytics import Analytics
from Connectors.IG import IG
from Connectors.dropbox_cache import DropBoxCache
from Connectors.tiingo import Tiingo
from BL.utils import ConfigReader
import dropbox
from Connectors.dropboxservice import DropBoxService
from UI.base_viewer import BaseViewer
from UI.plotly_viewer import PlotlyViewer

conf_reader = ConfigReader()
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx,"DEMO")
cache = DropBoxCache(ds)
tiingo = Tiingo(conf_reader=conf_reader, cache=cache)
ig = IG(conf_reader=conf_reader)
viewer = PlotlyViewer(cache)
#viewer = BaseViewer()

ig.create_report(ti=tiingo,
                 dp_service=ds,
                 cache=cache,
                 dp=DataProcessor(),
                 analytics=Analytics(),
                 viewer=viewer)
