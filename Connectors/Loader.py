import pandas as pd
import yfinance as yf
from finta import TA
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


