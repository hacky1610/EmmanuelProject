import gym
import gym_anytrading
from stable_baselines.common.vec_env import DummyVecEnv
from stable_baselines import A2C

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

def loadData(file):
    df = pd.read_csv(file)
    df["Date"] = pd.to_datetime(df["Date"])
    df.set_index("Date", inplace=True)
    return df

def doRandTest(env):
    state = env.reset()
    while True:
        action = env.action_space.sample()
        n_state, reward, done, info = env.step(action)
        if done:
            print(info)
            break
    plt.figure(figsize=(15, 6))
    plt.cla()
    env.render_all()
    plt.show()

def Evaluate(env,model):
    obs = env.reset()
    while True:
        obs = obs[np.newaxis,...]
        action, _states = model.predict(obs)
        obs, reward, done, info = env.step(action)
        if done:
            print(info)
            break
    plt.figure(figsize=(15, 6))
    plt.cla()
    env.render_all()
    plt.show()

def learn(model):
    #Todo: Callback -> https://youtu.be/D9sU1hLT0QY?t=1796
    model.learn(total_timesteps=100000) #ACER or PPo auch möglich

def createAndLearn(df):
    envTrain = gym.make('stocks-v0', df=df, frame_bound=(10, 100),
                        window_size=5)  # Why 5? See here https://youtu.be/D9sU1hLT0QY?t=949
    env_maker = lambda: envTrain
    envTrain = DummyVecEnv([env_maker])
    model = A2C('MlpLstmPolicy', envTrain, verbose=1)
    learn(model)
    return model

df = loadData("./Data/gmedata.csv")
#Learn
#model = createAndLearn(df)
#model.save("./model.h5")

#Evaluate
model = A2C.load("./model.h5")
envTest = gym.make('stocks-v0', df=df, frame_bound=(90, 110), window_size=5) #Day 90 to 110
Evaluate(envTest, model)
