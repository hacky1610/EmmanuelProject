from Connectors.IG import IG
from Envs.forexEnv import ForexEnv,Actions



class IgEnv(ForexEnv):

    def __init__(self,config: dict):
        super().__init__(config)
        #IG
        self.ig = IG()
        self.symbol = "CS.D.GBPUSD.CFD.IP"

    def trade(self, action):
        if action == Actions.Buy.value:
            self.ig.buy(self.symbol)
        else:
            if self.ig.has_opened_positions():
                deal = self.ig.get_opened_position_id()
                self.ig.sell(deal)

    def _get_observation(self):
        obs = self.signal_features[(len(self.signal_features) - self.window_size ):]
        return obs



