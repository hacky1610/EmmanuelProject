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
        self.data = Loader.getStockDataVec(config.get("stock_name"))
        self.agent = QlAgent(shape=(len(self.data),10),gamma=config.get("gamma",0.95),lr=config.get("lr",0.001))
        self.l = len(self.data) - 1
        self.batch_size = 32
        self.windows_size = 10
        self._tracer:Tracer = config.get("tracer",Tracer())
        self._limit = 10
        self._stop = 10

    def step(self):
        self.iter += 1

        self._tracer.write(f"Step {self.iter}")

        state = self.data[0:self.windows_size]
        total_profit = 0
        self.agent.inventory = []

        for t in range(self.l):
            action = self.agent.act(state)

            # sit
            next_state = self.data[t:t+self.windows_size]
            reward = 0

            current_price = self.data["Close"][t]

            for i in range(t, len(self.data)):
                futurePrice = self.data["Close"][i]
                if (action == 0): #Buy
                    if futurePrice > current_price + self._limit:
                        reward =  futurePrice - current_price
                        break
                    elif futurePrice < current_price - self._stop:
                        reward = futurePrice - current_price
                        break
                elif action == 1: #Sell
                    if futurePrice < current_price - self._limit:
                        reward =  current_price - futurePrice
                        break
                    elif futurePrice > current_price + self._stop:
                        reward =  current_price - futurePrice
                        break

            total_profit += reward
            reward = max(reward, 0)
            done = True if t == self.l - 1 else False
            self.agent.memory.append((state, action, reward, next_state, done))
            state = next_state

            if done:
                self._tracer.write("--------------------------------")
                self._tracer.write("Total Profit: " + Utils.formatPrice(total_profit))
                self._tracer.write("--------------------------------")

            if len(self.agent.memory) > self.batch_size:
                self.agent.expReplay(self.batch_size)


        if self.iter % 2 == 0:
            #self.agent.model.save("Models/model_ep" + str(self.iter))
            self._tracer.write("Model can be saved (own logic)")
        return {"num_resets": self.num_resets, "done": False, "total_profit": total_profit}

    def save_checkpoint(self, chkpt_dir):
        checkpoint_path = os.path.join(chkpt_dir, "model.h5")
        self.agent.model.save(checkpoint_path)
        self._tracer.write(f"Model saved (function save_checkpoint) under path {checkpoint_path}")
        return chkpt_dir

    def load_checkpoint(self, item):
        self.iter = item["iter"]

    def reset_config(self, new_config):
        self._tracer.write("reset_config called")
        if "fake_reset_not_supported" in self.config:
            return False
        self.num_resets += 1
        return True
