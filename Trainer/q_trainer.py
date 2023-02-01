from ray.tune import Trainable
from ray import tune
from Agents.QlAgent import QlAgent
from Connectors.Loader import Loader
import numpy as np
import math

def formatPrice(n):
	return ("-$" if n < 0 else "$") + "{0:.2f}".format(abs(n))

# returns the vector containing stock data from a fixed file
def getStockDataVec(key):
	vec = []
	lines = open("data/" + key + ".csv", "r").read().splitlines()

	for line in lines[1:]:
		vec.append(float(line.split(",")[4]))

	return vec

# returns the sigmoid
def sigmoid(x):
	return 1 / (1 + math.exp(-x))

# returns an an n-day state representation ending at time t
def getState(data, t, n):
	d = t - n + 1
	block = data[d:t + 1] if d >= 0 else -d * [data[0]] + data[0:t + 1] # pad with t0
	res = []
	for i in range(n - 1):
		res.append(sigmoid(block[i + 1] - block[i]))

	return np.array([res])

class QTrainer(Trainable):
    def setup(self, config):
        self.config = config
        self.num_resets = 0
        self.iter = 0
        self.agent = QlAgent(10)
        self.data = Loader.getStockDataVec("GSPC")
        self.l = len(self.data) - 1
        self.batch_size = 32
        self.windows_size = 10


    def step(self):
        self.iter += 1

        print(f"Step {self.iter}")

        state = getState( self.data, 0, self.windows_size + 1)

        total_profit = 0
        self.agent.inventory = []

        for t in range(self.l):
            action = self.agent .act(state)

            # sit
            next_state = getState( self.data, t + 1, self.windows_size + 1)
            reward = 0

            if action == 1:  # buy
                self.agent.inventory.append( self.data[t])
                print("Buy: " + formatPrice( self.data[t]))

            elif action == 2 and len(self.agent .inventory) > 0:  # sell
                bought_price = self.agent.inventory.pop(0)
                reward = max( self.data[t] - bought_price, 0)
                total_profit +=  self.data[t] - bought_price
                print("Sell: " + formatPrice( self.data[t]) + " | Profit: " + formatPrice( self.data[t] - bought_price))

            done = True if t == self.l - 1 else False
            self.agent.memory.append((state, action, reward, next_state, done))
            state = next_state

            if done:
                print("--------------------------------")
                print("Total Profit: " + formatPrice(total_profit))
                print("--------------------------------")

            if len(self.agent .memory) > self.batch_size:
                self.agent .expReplay(self.batch_size)

        if self.iter % 2 == 0:
            self.agent.model.save("Models/model_ep" + str(self.iter))
        return {"num_resets": self.num_resets, "done": False, "total_profit":total_profit}

    def save_checkpoint(self, chkpt_dir):
        return {"iter": self.iter}

    def load_checkpoint(self, item):
        self.iter = item["iter"]

    def reset_config(self, new_config):
        if "fake_reset_not_supported" in self.config:
            return False
        self.num_resets += 1
        return True