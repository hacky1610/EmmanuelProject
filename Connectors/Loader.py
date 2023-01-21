import pandas as pd
import yfinance as yf
from finta import TA
class Loader:

    @staticmethod
    def loadFromFile(file):
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
    @staticmethod
    def loadFromOnline(stock, start, end,interval="60m"):
        df = yf.download(stock, start, end, interval )
        df['SMA'] = TA.SMA(df, 12)
        df['RSI'] = TA.RSI(df,period=14)
        df['ROC'] = TA.ROC(df, period=10)
        df['%R'] = TA.WILLIAMS(df,period=14)
        #df['OBV'] = TA.OBV(df)
        md = TA.MACD(df)
        df['MACD'] = md['MACD']
        df['SIGNAL'] = md['SIGNAL']
        df.drop(columns=["Volume"], inplace=True)
        df.drop(columns=["Dividends"], inplace=True)
        df.drop(columns=["Stock Splits"], inplace=True)

        df.fillna(0, inplace=True)
        return df