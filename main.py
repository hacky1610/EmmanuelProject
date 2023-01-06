from Envs.StockSignalEnv import StockSignalEnv
from finta import TA
import pandas as pd
from Agents.Renotte import Renotte
from matplotlib import pyplot as plt

def loadData(file):
    df = pd.read_csv(file)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Volume"] = df["Volume"].apply(lambda x: float(x.replace(",", ""))) #From String to float
    df.sort_values("Date", ascending=True, inplace=True)
    df.set_index("Date", inplace=True)
    df['SMA'] = TA.SMA(df, 12)
    df['RSI'] = TA.RSI(df)
    df['OBV'] = TA.OBV(df)
    df.fillna(0, inplace=True)
    return df

df = loadData("./Data/gmedata.csv")
agent = Renotte(plt)

#Learn
envTrain = StockSignalEnv(df=df, frame_bound=(12, 50),window_size=12)  # Why 5? See here https://youtu.be/D9sU1hLT0QY?t=949
agent.createAndLearn(envTrain)

#Evaluate
envTest = StockSignalEnv( df=df, frame_bound=(80, 250), window_size=12) #Day 90 to 110
agent.Evaluate(envTest)
