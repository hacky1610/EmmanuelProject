from pandas import DataFrame
from finta import TA

class DataProcessor:

    def addSignals(self, df: DataFrame):
        df['SMA'] = TA.SMA(df, 12)
        df['RSI'] = TA.RSI(df, period=14)
        df['ROC'] = TA.ROC(df, period=10)
        df['%R'] = TA.WILLIAMS(df, period=14)
        md = TA.MACD(df)
        df['MACD'] = md['MACD']
        df['SIGNAL'] = md['SIGNAL']

    def clean_data(self, df: DataFrame):
        DataProcessor.drop_column(df, "Volume")
        DataProcessor.drop_column(df, "Dividends")
        DataProcessor.drop_column(df, "Stock Splits")
        df.fillna(0, inplace=True)

    @staticmethod
    def drop_column(df: DataFrame, name: str):
        if name in df.columns:
            df.drop(columns=[name], inplace=True)