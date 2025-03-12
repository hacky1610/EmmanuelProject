import hashlib
from BL import DataProcessor
from pandas import DataFrame
import pandas as pd


class DataFrameCache:
    def __init__(self, dataprocessor:DataProcessor):
        """
        Initialize with 1-hour OHLC DataFrame.
        :param ohlc_1h_df: DataFrame with 1-hour OHLC data.
        """
        self._4h_cache = {}
        self._12h_cache = {}
        self._1d_cache = {}
        self._dp = dataprocessor

    def _get_hash(self, df: DataFrame) -> str:
        # DataFrame in einen stringbasierten Repräsentationswert umwandeln
        df_string = df.to_csv(index=False)

        # Einen Hash (z.B. SHA-256) auf den stringbasierten Wert anwenden
        hash_object = hashlib.sha256(df_string.encode())
        return hash_object.hexdigest()

    def get_4h_df(self, df_1h_ohlc:DataFrame):

        """
        Returns the 4-hour DataFrame for the given 1-hour DataFrame index.
        :param index: The index in the 1-hour DataFrame.
        :return: The 4-hour DataFrame.
        """
        index = df_1h_ohlc.index[-1]
        df_4h = self._4h_cache.get(index, None)
        if df_4h is None:
            df_4h = self._convert_1h_to_4h(df_1h_ohlc)
            self._4h_cache[index] = df_4h
            return df_4h
        else:
            return df_4h

    def get_12h_df(self, df_1h_ohlc:DataFrame):

        """
        Returns the 4-hour DataFrame for the given 1-hour DataFrame index.
        :param index: The index in the 1-hour DataFrame.
        :return: The 4-hour DataFrame.
        """
        index = df_1h_ohlc.index[-1]
        df_12h = self._12h_cache.get(index, None)
        if df_12h is None:
            df_12h = self._convert_1h_to_12h(df_1h_ohlc)
            self._12h_cache[index] = df_12h
            return df_12h
        else:
            return df_12h

    def get_1d_df(self, df_1h_ohlc: DataFrame):

        """
        Returns the 4-hour DataFrame for the given 1-hour DataFrame index.
        :param index: The index in the 1-hour DataFrame.
        :return: The 4-hour DataFrame.
        """
        index = df_1h_ohlc.index[-1]
        df_24h = self._1d_cache.get(index, None)
        if df_24h is None:
            df_24h = self._convert_1h_to_24h(df_1h_ohlc)
            self._1d_cache[index] = df_24h
            return df_24h
        else:
            return df_24h

    def _convert_1h_to_12h(self, one_h_df: DataFrame):
        if one_h_df.empty:
            return DataFrame()

        one_h_df = one_h_df.copy()

        # Anzahl der Zeilen im DataFrame
        n = len(one_h_df)

        # Feste Endzeit setzen (erste Zeile bekommt diese Zeit)
        fixed_end_time = pd.Timestamp("2000-01-01 07:00:00")

        # Neue Zeiten rückwärts vergeben
        one_h_df['date_index'] = [fixed_end_time - pd.Timedelta(hours=(n - 1 - i)) for i in range(n)]

        # Gruppieren nach der neuen Zeitachse
        df_4h = one_h_df.groupby(pd.Grouper(key='date_index', freq='12h')).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last'
        }).dropna().reset_index()

        df_4h.drop(columns="date_index", inplace=True)

        self._dp.addSignals_big_tf(df_4h)

        return df_4h

    def _convert_1h_to_24h(self, one_h_df: DataFrame):
        if one_h_df.empty:
            return DataFrame()

        one_h_df = one_h_df.copy()

        # Anzahl der Zeilen im DataFrame
        n = len(one_h_df)

        # Feste Endzeit setzen (erste Zeile bekommt diese Zeit)
        fixed_end_time = pd.Timestamp("2000-01-01 07:00:00")

        # Neue Zeiten rückwärts vergeben
        one_h_df['date_index'] = [fixed_end_time - pd.Timedelta(hours=(n - 1 - i)) for i in range(n)]

        # Gruppieren nach der neuen Zeitachse
        df_4h = one_h_df.groupby(pd.Grouper(key='date_index', freq='24h')).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last'
        }).dropna().reset_index()

        df_4h.drop(columns="date_index", inplace=True)

        self._dp.addSignals_big_tf(df_4h)

        return df_4h

    def _convert_1h_to_4h(self, one_h_df: DataFrame):
        if one_h_df.empty:
            return DataFrame()

        one_h_df = one_h_df.copy()

        # Anzahl der Zeilen im DataFrame
        n = len(one_h_df)

        # Feste Endzeit setzen (erste Zeile bekommt diese Zeit)
        fixed_end_time = pd.Timestamp("2000-01-01 07:00:00")

        # Neue Zeiten rückwärts vergeben
        one_h_df['date_index'] = [fixed_end_time - pd.Timedelta(hours=(n - 1 - i)) for i in range(n)]

        # Gruppieren nach der neuen Zeitachse
        df_4h = one_h_df.groupby(pd.Grouper(key='date_index', freq='4h')).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last'
        }).dropna().reset_index()

        df_4h.drop(columns="date_index", inplace=True)

        self._dp.addSignals_big_tf(df_4h)

        return df_4h

    def reset(self):
        self._4h_cache = {}
        self._12h_cache = {}
        self._1d_cache = {}

