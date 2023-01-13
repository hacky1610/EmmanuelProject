from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3 import A2C, PPO, DQN, TD3, SAC
import numpy as np
from datetime import datetime
import os
import random
import string
from Agents import config
from stable_baselines3.common.noise import NormalActionNoise
from stable_baselines3.common.noise import OrnsteinUhlenbeckActionNoise

MODELS = {"A2C": A2C, "TD3": TD3, "SAC": SAC, "PPO": PPO, "DQN": DQN} #"DDPG": DDPG
MODEL_KWARGS = {x: config.__dict__[f"{x.upper()}_PARAMS"] for x in MODELS.keys()}

NOISE = {
    "normal": NormalActionNoise,
    "ornstein_uhlenbeck": OrnsteinUhlenbeckActionNoise,
}


class Renotte:
    _modelPath = ""
    _plotType = ""  # Types: show , save, none
    _logDirectory = ""
    _tfLogDirectory = None
    _plotPath = ""
    runName = ""
    _tracer = None
    _model = ""
    _discountRate = 0.95
    _policy = None
    totalReward = None
    totalProfit = None
    _modelKwargs = None
    _policyKwargs = None
    _seed = None

    def __init__(self, plot, tracer, plotType="show", tfLog=False, model="A2C", disountRate=0.99, policy="MlpPolicy",
                 logDir="/tmp", model_kwargs=None, policy_kwargs=None, seed=None ):
        if model not in MODELS:
            raise NotImplementedError("NotImplementedError")
        if model_kwargs is None:
            self._modelKwargs = MODEL_KWARGS[model]
        else:
            self._modelKwargs = model_kwargs

        if "action_noise" in self._modelKwargs:
            n_actions = self.env.action_space.shape[-1]
            self._modelKwargs["action_noise"] = NOISE[self._modelKwargs["action_noise"]](
                mean=np.zeros(n_actions), sigma=0.1 * np.ones(n_actions)
            )

        self._plt = plot
        self.runName = datetime.now().strftime("%Y%m%d_%H%M%S") + self.get_random_string()
        self._logDirectory = os.path.join(logDir, self.runName)
        self._modelPath = os.path.join(self._logDirectory, "model.h5")
        self._plotPath = os.path.join(self._logDirectory, "graph.png")
        os.mkdir(self._logDirectory)

        self._plotType = plotType
        self._tracer = tracer
        self._modelType = model
        self._discountRate = disountRate
        self._policy = policy
        self._policyKwargs = policy_kwargs
        self._seed = seed

        if tfLog:
            self._tfLogDirectory = self._logDirectory

    def plot(self, env):
        if "none" == self._plotType:
            return

        self._plt.figure(figsize=(15, 6))
        self._plt.cla()
        env.render_all()
        if "show" == self._plotType:
            self._plt.show()
        else:
            self._plt.savefig(self._plotPath)

    def doRandTest(self, env):
        state = env.reset()
        while True:
            action = env.action_space.sample()
            n_state, reward, done, info = env.step(action)
            if done:
                print(info)
                break
        self.plot(env)

    def Evaluate(self, env):
        self._tracer.Info("Run: {}".format(self.runName))
        obs = env.reset()
        while True:
            obs = obs[np.newaxis, ...]
            action, _states = self._model.predict(obs)
            obs, reward, done, info = env.step(action)
            if done:
                self._tracer.Result(info)
                self.totalReward = info["total_reward"]
                self.totalProfit = info["total_profit"]
                break
        self.plot(env)

    def learn(self):
        # Todo: Callback -> https://youtu.be/D9sU1hLT0QY?t=1796
        #self._model.learn(total_timesteps=1000000)
        self._model.learn(total_timesteps=10000)

    def loadModel(self):
        self._model = MODELS[self._modelType].load(self._modelPath)

    def createAndLearn(self, env):
        env_maker = lambda: env
        envTrain = DummyVecEnv([env_maker])

        self._model = MODELS[self._modelType](self._policy, envTrain, verbose=1, tensorboard_log=self._tfLogDirectory,
                                          gamma=self._discountRate,policy_kwargs=self._policyKwargs,seed=self._seed,  **self._modelKwargs)
        self.learn()
        self._model.save(self._modelPath)

    def get_random_string(self):
        # choose from all lowercase letter
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(4))
