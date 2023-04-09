from Connectors.IG import IG
from Connectors.tiingo import Tiingo
from BL.utils import ConfigReader
import dropbox
from Connectors.dropboxservice import DropBoxService


conf_reader = ConfigReader()
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx,"DEMO")
tiingo = Tiingo(conf_reader=conf_reader)
ig = IG(conf_reader=conf_reader)

ig.create_report(tiingo,ds)
