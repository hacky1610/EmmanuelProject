from Connectors.IG import IG
from Connectors.tiingo import Tiingo

symbol = "GBPUSD"
tiingo = Tiingo()
ig = IG()

ig.create_report(tiingo)
