from Connectors.IG import IG
from Envs.forexEnv import ForexEnv, Actions


class IgEnv(ForexEnv):

    def __init__(self, config: dict):
        super().__init__(config)
        # IG
        self.ig = IG()
        self.symbol = "CS.D.GBPUSD.CFD.IP"

    def exit_position(self, action: Actions):
        if self.ig.has_opened_positions():
            self.tracer.write("There are still open positions")
            directionToSearch = Actions.get_name(Actions.opposite(action))
            direction = Actions.get_name(action)
            positions = self.ig.get_opened_position_ids_by_direction(directionToSearch)
            for p in positions.iterrows():
                dealid = p[1]["dealId"]
                self.tracer.write(f"Exit position with id {dealid}")
                self.ig.exit(dealid, direction)

    def trade(self, action_value):
        self.tracer.write(f"Got a {Actions.get_name_by_value(action_value)} signal")
        action = Actions.get_enum_by_value(action_value)

        self.exit_position(action)

        if self.ig.has_opened_positions():  # Aktuell wird nur eine Pos gehalten
            self.tracer.write(f"Dont trade because there are open positions")
            return

        if action == Actions.Buy:
            self.tracer.write("Open Buy Trade")
            self.ig.buy(self.symbol)
        else:
            self.tracer.write("Open Sell Trade")
            self.ig.sell(self.symbol)

    def _get_observation(self):
        obs = self.signal_features[(len(self.signal_features) - self.window_size):]
        return obs
