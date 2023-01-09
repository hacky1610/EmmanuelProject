from Envs.StockSignalEnv import StockSignalEnv
from finta import TA
import pandas as pd
from Agents.Renotte import Renotte
from matplotlib import pyplot as plt
from Tracing.FileTracer import FileTracer


def loadData(file):
    df = pd.read_csv(file)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Volume"] = df["Volume"].apply(lambda x: float(x.replace(",", "")))  # From String to float
    df.sort_values("Date", ascending=True, inplace=True)
    df.set_index("Date", inplace=True)
    df['SMA'] = TA.SMA(df, 12)
    df['RSI'] = TA.RSI(df)
    df['OBV'] = TA.OBV(df)
    df.fillna(0, inplace=True)
    return df


df = loadData("../../Data/allianzdata.csv")
tracer = FileTracer("../../trace.log")

agents = [Renotte(plt, tracer=tracer, plotType="save", model="PPO2"),
          Renotte(plt, tracer=tracer, plotType="save", model="DQN"),
          Renotte(plt, tracer=tracer, plotType="save", model="A2C"),
          Renotte(plt, tracer=tracer, plotType="save", model="PPO2",disountRate=0.95),
          Renotte(plt, tracer=tracer, plotType="save", model="DQN",disountRate=0.95),
          Renotte(plt, tracer=tracer, plotType="save", model="A2C",disountRate=0.95)]

for a in agents:
    envTrain = StockSignalEnv(df=df, frame_bound=(80, 150),
                              window_size=12)  # Why 5? See here https://youtu.be/D9sU1hLT0QY?t=949
    a.doRandTest(envTrain)
    a.createAndLearn(envTrain)
    # Evaluate
    envTest = StockSignalEnv(df=df, frame_bound=(145, 170), window_size=12)
    a.loadModel()
    a.Evaluate(envTest)
    del a


