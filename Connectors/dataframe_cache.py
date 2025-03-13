import hashlib
from BL import DataProcessor
from pandas import DataFrame
import pandas as pd


class DataFrameCache:
    def __init__(self, dataprocessor: DataProcessor):
        """
        Initialize with 1-hour OHLC DataFrame.
        :param ohlc_1h_df: DataFrame with 1-hour OHLC data.
        """
        self._4h_cache = {}
        self._12h_cache = {}
        self._1d_cache = {}
        self._dp = dataprocessor

    def init_caches(self, df):
        self._build_cache_4h(df)
        self._build_cache_12h(df)
        self._build_cache_24h(df)

    def _build_cache(self, one_h_df: DataFrame, hours: int, cache_attr, convert_func):
        if one_h_df.empty:
            return

        setattr(self, cache_attr, {})

        self._original_1h_df = one_h_df.filter(["open", "high", "low", "close"])

        length = len(self._original_1h_df)

        for shift in range(hours):
            start_index = max(1, length - shift)  # Mindestens 1 Eintrag sicherstellen

            subset = self._original_1h_df.iloc[:start_index]
            if subset.empty:
                continue  # Falls subset trotzdem leer ist, überspringen

            index = self._original_1h_df.iloc[:start_index].index[-1] % hours

            getattr(self, cache_attr)[index] = convert_func(subset)

    def _build_cache_4h(self, one_h_df: DataFrame):
        self._build_cache(one_h_df, 4, "_4h_cache", self._convert_1h_to_4h)

    def _build_cache_12h(self, one_h_df: DataFrame):
        self._build_cache(one_h_df, 12, "_12h_cache", self._convert_1h_to_12h)

    def _build_cache_24h(self, one_h_df: DataFrame):
        self._build_cache(one_h_df, 24, "_24h_cache", self._convert_1h_to_24h)

    def _get_cache(self, df_1h_ohlc: DataFrame, cache_attr, hours):

        cache = getattr(self, cache_attr)

        if not cache:
            raise ValueError("Cache wurde nicht erstellt. Rufe zuerst _build_cache auf!")

        if df_1h_ohlc.empty:
            return DataFrame()

        index = df_1h_ohlc.index[-1] % hours

        df_4h = cache[index]

        # Anzahl der 4h-Blöcke bestimmen
        # Maximale Anzahl an 4h-Blöcken bestimmen
        max_entries = (len(self._original_1h_df) - len(df_1h_ohlc)) // hours
        if max_entries > 0:
            return df_4h.iloc[:max_entries * -1].copy()
        else:
            return df_4h

    def get_4h_df(self, df_1h_ohlc: DataFrame):

        return self._get_cache(df_1h_ohlc, "_4h_cache",4)

    def get_12h_df(self, df_1h_ohlc: DataFrame):

        return self._get_cache(df_1h_ohlc, "_12h_cache",12)

    def get_1d_df(self, df_1h_ohlc: DataFrame):

        return self._get_cache(df_1h_ohlc, "_24h_cache",24)

    def _convert_1h_to_12h(self, one_h_df: DataFrame):
        return self._convert_1h_to_x(one_h_df, 12, "2000-01-01 11:59:00")

    def _convert_1h_to_24h(self, one_h_df: DataFrame):
        return self._convert_1h_to_x(one_h_df, 24,"2000-01-01 23:59:00")

    def _convert_1h_to_4h(self, one_h_df: DataFrame):
        return self._convert_1h_to_x(one_h_df, 4,"2000-01-01 07:00:00")

    def _convert_1h_to_x(self, one_h_df: DataFrame, hours, time):
        if one_h_df.empty:
            return DataFrame()

        one_h_df = one_h_df.copy()

        # Anzahl der Zeilen im DataFrame
        n = len(one_h_df)

        # Feste Endzeit setzen (erste Zeile bekommt diese Zeit)
        fixed_end_time = pd.Timestamp(time)

        # Neue Zeiten rückwärts vergeben
        one_h_df['date_index'] = [fixed_end_time - pd.Timedelta(hours=(n - 1 - i)) for i in range(n)]
        #one_h_df['date_index'] = one_h_df['date_index'].dt.floor(f'{hours}H')

        # Gruppieren nach der neuen Zeitachse
        df_4h = one_h_df.groupby(pd.Grouper(key='date_index', freq=f'{hours}h')).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last'
        }).dropna().reset_index()

        df_4h.drop(columns="date_index", inplace=True)

        self._dp.addSignals_big_tf(df_4h)

        return df_4h

    def reset(self):
        self._4h_cache.clear()
        self._12h_cache.clear()
        self._1d_cache.clear()
