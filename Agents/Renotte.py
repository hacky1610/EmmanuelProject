from stable_baselines.common.vec_env import DummyVecEnv
from stable_baselines import A2C

class Renotte:
    _modelPath = "./model.h5"
    def __init__(self,plot):
        self._model = ""
        self._plt = plot


    def doRandTest(self,env):
        state = env .reset()
        while True:
            action = env .action_space.sample()
            n_state, reward, done, info = env.step(action)
            if done:
                print(info)
                break
        self._plt.figure(figsize=(15, 6))
        self._plt.cla()
        self._plt.render_all()
        self._plt.show()

    def Evaluate(self,env):
        obs = env.reset()
        while True:
            obs = obs[np.newaxis, ...]
            action, _states = self._model.predict(obs)
            obs, reward, done, info = env.step(action)
            if done:
                print(info)
                break
        self._plt.figure(figsize=(15, 6))
        self._plt.cla()
        self._plt.render_all()
        self._plt.show()

    def learn(self):
        # Todo: Callback -> https://youtu.be/D9sU1hLT0QY?t=1796
        self._model.learn(total_timesteps=1000000)  # ACER or PPo auch möglich

    def loadModel(self):
        self._model = A2C.load(self._modelPath)

    def createAndLearn(self, env):
        env_maker = lambda: env
        envTrain = DummyVecEnv([env_maker])
        self._model = A2C('MlpLstmPolicy', envTrain, verbose=1)
        self.learn()
        self._model.save("./model.h5")
