import os.path

import pandas as pd
from Agents.Renotte import Renotte
from Envs.StockSignalEnv import StockSignalEnv


class AgentCollection:
    runs = None

    def loadFromFile(self, file):
        self.runs = pd.read_csv(file)
        self.runs["Reward"] = None
        self.runs["Profit"] = None
        self.runs["RunName"] = None

    def CreateAgent(plt, tracer, run, logdir):
        return Renotte(plt, tracer=tracer, model=run["Model"], disountRate=float(run["Discount"]), plotType="save",
                       logDir=logdir)

    def Run(self, df, plt, tracer, logdir):
        for i, run in self.runs.iterrows():
            ag = AgentCollection.CreateAgent(plt, tracer, run, logdir)

            env_train = StockSignalEnv(df=df, frame_bound=(12, 100),
                                      window_size=12)  # Why 5? See here https://youtu.be/D9sU1hLT0QY?t=949
            ag.createAndLearn(env_train)
            # Evaluate
            env_test = StockSignalEnv(df=df, frame_bound=(100, 125), window_size=12)
            ag.loadModel()
            ag.Evaluate(env_test)

            self.runs._set_value(i, "Reward", ag.totalReward)
            self.runs._set_value(i, "Profit", ag.totalProfit)
            self.runs._set_value(i, "RunName", ag.runName)
            del ag

        self.runs.to_csv(os.path.join("Result.csv"))
