from Connectors.IG import IG
from Connectors.tiingo import Tiingo
from BL.utils import ConfigReader

conf_reader = ConfigReader()
tiingo = Tiingo(conf_reader=conf_reader)
ig = IG(conf_reader=conf_reader)

ig.create_report(tiingo)
