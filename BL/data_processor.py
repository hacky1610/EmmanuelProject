from pandas import DataFrame
from finta import TA

class DataProcessor:

    def addSignals(self, df: DataFrame):
        df['SMA_10'] = TA.SMA(df, 10)
        df['SMA_10_LOW'] = TA.SMA(df, 10,column="low")
        df['SMA_10_HIGH'] = TA.SMA(df, 10, column="high")
        df['EMA'] = TA.EMA(df)
        df['EMA_10'] = TA.EMA(df,10)
        df['EMA_14'] = TA.EMA(df, 14)
        df['EMA_20'] = TA.EMA(df, 20)
        df['EMA_30'] = TA.EMA(df,30)
        df['EMA_50'] = TA.EMA(df, 50)

        bb= TA.BBANDS(df)
        df['BB_UPPER'] = bb['BB_UPPER']
        df['BB_MIDDLE'] = bb['BB_MIDDLE']
        df['BB_LOWER'] = bb['BB_LOWER']
        bb1 = TA.BBANDS(df,std_multiplier=1)
        df['BB1_UPPER'] = bb1['BB_UPPER']
        df['BB1_MIDDLE'] = bb1['BB_MIDDLE']
        df['BB1_LOWER'] = bb1['BB_LOWER']

        df['RSI'] = TA.RSI(df, period=14)
        df['RSI_7'] = TA.RSI(df, period=7)
        df['RSI_21'] = TA.RSI(df, period=21)
        df['ROC'] = TA.ROC(df, period=10)
        df['%R'] = TA.WILLIAMS(df, period=14)
        md = TA.MACD(df)
        df['MACD'] = md['MACD']
        df['SIGNAL'] = md['SIGNAL']
        df["CCI"] = TA.CCI(df)
        df["CCI_7"] = TA.CCI(df,7)

        df["STOCHK"] = TA.STOCH(df)
        df["STOCHD"] = TA.STOCHD(df,stoch_period=5)
        df["STOCHD_21"] = TA.STOCH(df,period=21)
        df["STOCHD_30"] = TA.STOCH(df, period=21)
        df["ADX"] = TA.ADX(df, period=9)

        df["ATR"] = TA.ATR(df)

    def clean_data(self, df: DataFrame):
        DataProcessor.drop_column(df, "Volume")
        DataProcessor.drop_column(df, "Dividends")
        DataProcessor.drop_column(df, "Stock Splits")
        df.dropna( inplace=True)
        df.reset_index(inplace=True)
        df.drop(columns=["index"], inplace=True)
        df.reset_index(inplace=True)

    @staticmethod
    def drop_column(df: DataFrame, name: str):
        if name in df.columns:
            df.drop(columns=[name], inplace=True)