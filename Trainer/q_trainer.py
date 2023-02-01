from ray.tune import Trainable
from ray import tune

class QTrainer(Trainable):
    def setup(self, config):
        self.config = config
        self.num_resets = 0
        self.iter = 0


    def step(self):
        self.iter += 1

        print(f"Step {self.iter}")
        return {"num_resets": self.num_resets, "done": False, "episode_reward_mean":3}

    def save_checkpoint(self, chkpt_dir):
        return {"iter": self.iter}

    def load_checkpoint(self, item):
        self.iter = item["iter"]

    def reset_config(self, new_config):
        if "fake_reset_not_supported" in self.config:
            return False
        self.num_resets += 1
        return True