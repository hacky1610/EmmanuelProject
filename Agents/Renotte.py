from stable_baselines.common.vec_env import DummyVecEnv
from stable_baselines import A2C,PPO2,DQN
from stable_baselines.common import make_vec_env
import numpy as np
from datetime import datetime
import os
import random
import string
import Tracing.Tracer

class Renotte:
    _modelPath = ""
    _plotType = "" #Types: show , save, none
    _logDirectory = ""
    _tfLogDirectory = None
    _plotPath = ""
    _runName = ""
    _tracer = None
    _model = ""
    _discountRate = 0.95

    def __init__(self, plot,tracer, plotType="show", tfLog=False, model="A2C", disountRate=0.99):
        self._plt = plot
        self._runName = datetime.now().strftime("%Y%m%d_%H%M%S") + self.get_random_string()
        self._logDirectory = os.path.join("runs",self._runName )
        self._modelPath = os.path.join(self._logDirectory, "model.h5")
        self._plotPath = os.path.join(self._logDirectory, "graph.png")
        os.mkdir(self._logDirectory)

        self._plotType = plotType
        self._tracer = tracer
        self._model = model
        self._discountRate = disountRate

        if tfLog == True:
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
        state = env .reset()
        while True:
            action = env .action_space.sample()
            n_state, reward, done, info = env.step(action)
            if done:
                print(info)
                break
        self.plot(env)

    def Evaluate(self,env):
        self._tracer.Info("Run: {}".format(self._runName))
        obs = env.reset()
        while True:
            obs = obs[np.newaxis, ...]
            action, _states = self._model.predict(obs)
            obs, reward, done, info = env.step(action)
            if done:
                self._tracer.Result(info)
                break
        self.plot(env)

    def learn(self):
        # Todo: Callback -> https://youtu.be/D9sU1hLT0QY?t=1796
        self._model.learn(total_timesteps=1000000)  # ACER or PPo auch möglich
        #self._model.learn(total_timesteps=10000)  # ACER or PPo auch möglich

    def loadModel(self):
        if "A2C" == self._model:
            self._model = A2C.load(self._modelPath)
        elif "PPO2" == self._model:
            self._model = PPO2.load(self._modelPath)
        elif "DQN" == self._model:
            self._model = DQN.load(self._modelPath)

    def createAndLearn(self, env):
        env_maker = lambda: env
        envTrain = DummyVecEnv([env_maker])

        if "A2C" == self._model:
            self._model = A2C('MlpLstmPolicy', envTrain, verbose=1, tensorboard_log=self._tfLogDirectory,gamma=self._discountRate )
        elif "PPO2" == self._model:
            self._model = PPO2('MlpPolicy', envTrain, verbose=1, tensorboard_log=self._tfLogDirectory,gamma=self._discountRate )
        elif "DQN" == self._model:
            self._model = DQN('LnMlpPolicy', envTrain, verbose=1, tensorboard_log=self._tfLogDirectory,gamma=self._discountRate)

        self.learn()
        self._model.save(self._modelPath)

    def get_random_string(self):
        # choose from all lowercase letter
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(4))
