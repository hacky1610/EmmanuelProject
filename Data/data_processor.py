from pandas import DataFrame
from finta import TA

class DataProcessor:

    def addSignals(self, df: DataFrame):
        df['SMA7'] = TA.SMA(df, 7)
        df['SMA13'] = TA.SMA(df, 13)
        df['EMA'] = TA.EMA(df)
        bb= TA.BBANDS(df)
        df['BB_UPPER'] = bb['BB_UPPER']
        df['BB_MIDDLE'] = bb['BB_MIDDLE']
        df['BB_LOWER'] = bb['BB_LOWER']
        df['RSI'] = TA.RSI(df, period=14)
        df['ROC'] = TA.ROC(df, period=10)
        df['%R'] = TA.WILLIAMS(df, period=14)
        md = TA.MACD(df)
        df['MACD'] = md['MACD']
        df['SIGNAL'] = md['SIGNAL']
        df["CCI"] = TA.CCI(df)

    def clean_data(self, df: DataFrame):
        DataProcessor.drop_column(df, "Volume")
        DataProcessor.drop_column(df, "Dividends")
        DataProcessor.drop_column(df, "Stock Splits")
        df.dropna(0, inplace=True)
        df.reset_index(inplace=True)

    @staticmethod
    def drop_column(df: DataFrame, name: str):
        if name in df.columns:
            df.drop(columns=[name], inplace=True)