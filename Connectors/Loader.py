import pandas as pd
import yfinance as yf
from finta import TA
from pandas import DataFrame


class Loader:

    @staticmethod
    def loadFromFile(file):
        df = pd.read_csv(file)
        df["Date"] = pd.to_datetime(df["Date"])
        df["Volume"] = df["Volume"].apply(lambda x: float(x.replace(",", "")))  # From String to float
        df.sort_values("Date", ascending=True, inplace=True)
        df.set_index("Date", inplace=True)

        Loader.addSignals(df)
        Loader.clean_data(df)

        return df

    @staticmethod
    def loadFromOnline(stock, start, end, interval="60m"):
        df = yf.download(stock, start, end, interval)
        Loader.addSignals(df)
        Loader.clean_data(df)

        return df

    @staticmethod
    def addSignals(df: DataFrame):
        df['SMA'] = TA.SMA(df, 12)
        df['RSI'] = TA.RSI(df, period=14)
        df['ROC'] = TA.ROC(df, period=10)
        df['%R'] = TA.WILLIAMS(df, period=14)
        md = TA.MACD(df)
        df['MACD'] = md['MACD']
        df['SIGNAL'] = md['SIGNAL']

    @staticmethod
    def clean_data(df: DataFrame):
        Loader.drop_column(df,"Volume")
        Loader.drop_column(df,"Dividends")
        Loader.drop_column(df,"Stock Splits")
        df.fillna(0, inplace=True)

    @staticmethod
    def drop_column(df: DataFrame, name: str):
        if name in df.columns:
            df.drop(columns=[name], inplace=True)
