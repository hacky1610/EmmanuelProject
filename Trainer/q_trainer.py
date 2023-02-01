from ray.tune import Trainable
from Agents.QlAgent import QlAgent
from Connectors.Loader import Loader
from Utils import Utils
import os
from Tracing.Tracer import Tracer

class QTrainer(Trainable):
    def setup(self, config):
        self.config = config
        self.num_resets = 0
        self.iter = 0
        self.agent = QlAgent(10)
        self.data = Loader.getStockDataVec(config.get("stock_name"))
        self.l = len(self.data) - 1
        self.batch_size = 32
        self.windows_size = 10
        self._tracer:Tracer = config.get("tracer",Tracer())

    def step(self):
        self.iter += 1

        print(f"Step {self.iter}")

        state = Utils.getState(self.data, 0, self.windows_size + 1)
        total_profit = 0
        self.agent.inventory = []

        for t in range(self.l):
            action = self.agent.act(state)

            # sit
            next_state = Utils.getState(self.data, t + 1, self.windows_size + 1)
            reward = 0

            if action == 1:  # buy
                self.agent.inventory.append(self.data[t])
                #print("Buy: " + Utils.formatPrice(self.data[t]))

            elif action == 2 and len(self.agent.inventory) > 0:  # sell
                bought_price = self.agent.inventory.pop(0)
                reward = max(self.data[t] - bought_price, 0)
                total_profit += self.data[t] - bought_price
                self._tracer.write("Sell: " + Utils.formatPrice(self.data[t]) + " | Profit: " + Utils.formatPrice(
                    self.data[t] - bought_price))


            done = True if t == self.l - 1 else False
            self.agent.memory.append((state, action, reward, next_state, done))
            state = next_state

            if done:
                print("--------------------------------")
                print("Total Profit: " + Utils.formatPrice(total_profit))
                print("--------------------------------")

            if len(self.agent.memory) > self.batch_size:
                self.agent.expReplay(self.batch_size)


        #if self.iter % 2 == 0:
        #    self.agent.model.save("Models/model_ep" + str(self.iter))
        return {"num_resets": self.num_resets, "done": False, "total_profit": total_profit}

    def save_checkpoint(self, chkpt_dir):
        checkpoint_dir = Utils.get_models_dir()
        checkpoint_path = os.path.join(checkpoint_dir, "model_ep" + str(self.iter))
        self.agent.model.save(checkpoint_path)
        self._tracer.write("Model saved (function save_checkpoint)")
        return checkpoint_dir

    def load_checkpoint(self, item):
        self.iter = item["iter"]

    def reset_config(self, new_config):
        if "fake_reset_not_supported" in self.config:
            return False
        self.num_resets += 1
        return True
