import pandas as pd

import pandas as pd
from collections import Counter

from collections import Counter
import itertools

def remove_duplicates_with_unordered_list_column(df, subset, list_column):
    """
    Entfernt doppelte Zeilen aus einem DataFrame basierend auf bestimmten Spalten,
    wobei eine der Spalten eine Liste oder ein Array ist, deren Reihenfolge ignoriert wird.
    """
    if list_column not in subset:
        raise ValueError(f"Die Spalte '{list_column}' muss in der subset-Liste enthalten sein.")

    sorted_column = f'__sorted_{list_column}'
    df = df.copy()

    def normalize_to_tuple(x):
        try:
            return tuple(sorted(list(x)))
        except Exception:
            return x  # Wenn z.B. x ein einfacher String oder None ist

    df[sorted_column] = df[list_column].apply(normalize_to_tuple)

    subset_modified = [sorted_column if col == list_column else col for col in subset]

    df_cleaned = df.drop_duplicates(subset=subset_modified)
    df_cleaned = df_cleaned.drop(columns=[sorted_column])

    return df_cleaned

lin =  pd.read_parquet("C:\\Users\\adhada7\\Projects\\predictor_6.parquet")
win =  pd.read_parquet("C:\\Users\\adhada7\\Projects\\predictor_win_6.parquet")

                                #all_df = DataFrame()
all_df = pd.concat([lin, win], ignore_index=True)
all_df = remove_duplicates_with_unordered_list_column(
    all_df,
    ["_symbol", "_atr_factor_stop", "_atr_factor_limit", "_features", "_trade_mode"],
    "_features"
)
all_df.to_parquet("C:\\Users\\adhada7\\Projects\\predictor_win_6.parquet")
