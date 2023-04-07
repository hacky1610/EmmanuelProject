from Connectors.IG import IG
from Connectors.tiingo import Tiingo
from BL.utils import ConfigReader

symbol = "GBPUSD"
tiingo = Tiingo()
ig = IG(ConfigReader())

ig.create_report(tiingo)
