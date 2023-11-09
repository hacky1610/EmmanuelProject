from pandas import DataFrame
from finta import TA


class DataProcessor:

    @staticmethod
    def addSignals(df: DataFrame):


        df["ATR"] = TA.ATR(df)


        return



    @staticmethod
    def clean_data(df: DataFrame):
        DataProcessor.drop_column(df, "Volume")
        DataProcessor.drop_column(df, "Dividends")
        DataProcessor.drop_column(df, "Stock Splits")
        df.dropna(inplace=True)
        df.reset_index(inplace=True)
        df.drop(columns=["index"], inplace=True)
        df.reset_index(inplace=True)

    @staticmethod
    def drop_column(df: DataFrame, name: str):
        if name in df.columns:
            df.drop(columns=[name], inplace=True)



