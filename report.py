from Connectors.IG import IG
from Connectors.dropbox_cache import DropBoxCache
from Connectors.tiingo import Tiingo
from BL.utils import ConfigReader
import dropbox
from Connectors.dropboxservice import DropBoxService
from UI.plotly_viewer import PlotlyViewer

conf_reader = ConfigReader(account_type="LIVE")
ig = IG(conf_reader=conf_reader,acount_type="LIVE")

ig.create_report()
