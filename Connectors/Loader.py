import os.path
import pandas as pd
import sklearn.preprocessing
import yfinance as yf
from LSTM_Logic import Utils
from Data.data_processor import DataProcessor
from datetime import datetime

class Loader:

    @staticmethod
    def loadFromFile(file:str,data_processor:DataProcessor):
        df = pd.read_csv(file)
        df["Date"] = pd.to_datetime(df["Date"])
        df["Volume"] = df["Volume"].apply(lambda x: float(x.replace(",", "")))  # From String to float
        df.sort_values("Date", ascending=True, inplace=True)
        df.set_index("Date", inplace=True)

        data_processor.addSignals(df)
        data_processor.clean_data(df)

        return df

    @staticmethod
    def loadFromOnline(stock:str, start:datetime, end:datetime,data_processor:DataProcessor, interval:str="60m"):
        df = yf.download(stock, start, end, interval)
        data_processor.addSignals(df)
        data_processor.clean_data(df)

        return df

    # returns the vector containing stock data from a fixed file
    @staticmethod
    def getStockDataVec(key):
        path = os.path.join(Utils.get_project_dir(), "Data", f"{key}.csv")
        df = pd.read_csv(filepath_or_buffer=path,delimiter=",")
        df.drop(columns=["Date"],inplace=True)
        dp = DataProcessor()
        dp.addSignals(df)
        dp.clean_data(df)
        df.reset_index(inplace=True)
        signals =  df.loc[:, ['Close', 'SMA7','SMA13',"BB_UPPER",'BB_LOWER','BB_MIDDLE', 'RSI', 'ROC', '%R', 'MACD', 'SIGNAL']]
        scaler = sklearn.preprocessing.MinMaxScaler()
        signals[signals.columns] =  scaler.fit(signals).transform(signals)
        return signals

