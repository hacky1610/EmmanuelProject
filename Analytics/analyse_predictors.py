import pandas as pd
import statistics
import pandas as pd
from collections import Counter

from collections import Counter
import itertools

import pandas as pd
import numpy as np
from itertools import product


def find_best_train_filters(df):
    """
    Findet die besten Trainings-Filterkombinationen, um eine möglichst hohe mittlere _test_precision zu erzielen.

    Args:
        df (pd.DataFrame): DataFrame mit Spalten wie _train_precision, _train_reward, _train_trade_count, _train_variance,
                           _test_precision etc.

    Returns:
        Tuple[dict, pd.DataFrame, float]:
            - Beste Filterkombination als dict
            - Gefilterter DataFrame mit diesen Kriterien
            - Durchschnittlicher _test_precision-Wert
    """
    # Mögliche Filterwerte (kannst du gerne anpassen!)
    precision_thresholds = [0.5, 0.6, 0.7]
    reward_thresholds = [5, 10, 20]
    trade_count_thresholds = [10, 20, 30]
    variance_max = [1000, 500, 300]

    best_mean = -1
    best_filters = {}
    best_df = None

    # Alle Kombinationen durchprobieren
    for p, r, t, v in product(precision_thresholds, reward_thresholds, trade_count_thresholds, variance_max):
        filtered = df[
            (df['_train_precision'] >= p) &
            (df['_train_reward'] >= r) &
            (df['_train_trade_count'] >= t) &
            (df['_train_variance'] <= v)
            ]
        if len(filtered) == 0:
            continue

        test_precision_mean = filtered['_test_precision'].mean()
        if test_precision_mean > best_mean:
            best_mean = test_precision_mean
            best_filters = {
                'train_precision >= ': p,
                'train_reward >= ': r,
                'train_trade_count >= ': t,
                'train_variance <= ': v
            }
            best_df = filtered

    return best_filters, best_df, best_mean


def most_common_features(df):
    # Alle Listen in eine einzige lange Liste zusammenführen
    all_features = list(itertools.chain.from_iterable(df['_features']))

    # Zählen, wie oft jedes einzelne Feature vorkommt
    feature_counts = Counter(all_features)

    # Die 15 häufigsten Features
    top_15 = feature_counts.most_common(15)

    # Ausgabe
    for i, (feature, count) in enumerate(top_15, 1):
        print(f"{i:2d}. {feature} → {count}x")

def most_common_combo(df):
    # Beispiel: dein DataFrame
    # df = pd.read_csv(...)  # oder wie du ihn auch erzeugst

    # Liste normalisieren (Reihenfolge egal → set) und dann als frozenset (damit zählbar)
    feature_sets = df['_features'].apply(lambda x: frozenset(x))

    # Jetzt zählen
    counter = Counter(feature_sets)

    # Die 10 häufigsten Kombinationen (als frozenset) anzeigen
    top_10 = counter.most_common(10)

    # Optional: frozenset wieder in sortierte Liste umwandeln zur besseren Lesbarkeit
    top_10_readable = [(sorted(list(fs)), count) for fs, count in top_10]

    # Ausgabe
    for i, (features, count) in enumerate(top_10_readable, 1):
        print(f"{i:2d}. {features} → {count}x")

def analyze_by_symbol(df):
    required_columns = [
        '_symbol', '_train_precision', '_train_reward', '_test_precision',
        '_test_reward', '_test_trade_count', '_atr_factor_stop', '_atr_factor_limit'
    ]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in DataFrame: {missing}")

    grouped = df.groupby('_symbol')

    summary = grouped.agg({
        '_train_precision': ['mean', 'median'],
        '_train_reward': ['mean', 'median'],
        '_test_precision': ['mean', 'median'],
        '_test_reward': ['mean', 'median'],
        '_teFst_trade_count': ['sum'],
    })

    # Spaltennamen flach machen
    summary.columns = ['_'.join(col).strip() for col in summary.columns.values]
    summary = summary.rename(columns={'_symbol_count': 'num_entries'})

    return summary

def is_clustered(row, min_variance=80, min_span=200):
    indexes = row['_train_indexes']
    if indexes is None or len(indexes) < 2:
        return True
    span = max(indexes) - min(indexes)
    return row['_train_variance'] < min_variance and span < min_span

def analyze_df(df):
    print((df["_test_precision"] * 100).mean())
    print(df["_test_reward"].mean())
    print(df[df["_trade_mode"] == "sell"]["_test_precision"].mean())

    most_common_features(df)

    for i, row in df[["_atr_factor_stop", "_atr_factor_limit"]].drop_duplicates().iterrows():
        stop = row["_atr_factor_stop"]
        limit = row["_atr_factor_limit"]

        # 3. Filter anwenden
        gefiltert = df[(df["_atr_factor_stop"] == stop) & (df["_atr_factor_limit"] == limit)]

        print(f"Factor {stop} {limit} - {gefiltert['_test_precision'].mean()} {gefiltert['_test_reward'].mean()}")

    sum_prec = 0
    for symbol in set(df["_symbol"]):
        sum_prec += df[df._symbol == symbol]["_test_precision"].mean()
        print(
            f'{symbol} {df[df._symbol == symbol]["_test_precision"].mean()} {df[df._symbol == symbol]["_test_reward"].mean()} {len(df[df._symbol == symbol])}')

    df['features_len'] = df['_features'].apply(len)
    for f_len in set(df["features_len"]):
        print(
            f'{f_len} {df[df.features_len == f_len]["_test_precision"].mean()} {df[df.features_len == f_len]["_test_reward"].mean()} {len(df[df.features_len == f_len])}')

    print(f"Prec {sum_prec / len(set(df['_symbol']))}")
    print(f"Total count {len(df)}")

pd.set_option('display.max_columns', None)
df = pd.read_parquet("../predictor_5.parquet" )

print("Default")
analyze_df(df)


def filter_by_best_feature(top_count:int = 10, feature_count:int = 1):
    global top10_features, df_filtered
    df_exploded = df.explode('_features')
    # Gruppieren nach Feature
    summary = df_exploded.groupby('_features').agg(
        count=('_test_reward', 'count'),
        positive_count=('_test_reward', lambda x: (x > 0).sum()),
        avg_reward=('_test_reward', 'mean')
    )
    # Optional: Anteil positiver Rewards
    summary['positive_ratio'] = summary['positive_count'] / summary['count']
    # Sortieren nach z. B. durchschnittlichem Reward oder positivem Anteil
    summary = summary.sort_values(by='avg_reward', ascending=False)
    summary = summary[summary.positive_ratio > 0.66]
    summary['score'] = summary['avg_reward'] * summary['positive_ratio']
    top_features_by_score = summary.sort_values(by='score', ascending=False)
    top_features = summary.sort_values(by='avg_reward', ascending=False).head(top_count).index.tolist()
    # Annahme: df['_features'] ist eine Liste von Strings pro Zeile
    return df[df['_features'].apply(lambda feat_list: sum(f in top_features for f in feat_list) >= feature_count)]


train_filtered = df[
    (df['_train_precision'] > 0.6) &
    (df['_train_reward'] > 10) &
    (df['_train_variance'] >= 50) &
    (df['_train_trade_count'] >= 20) &
    (df['_train_variance'] < 300)
]


train_filtered = train_filtered[~train_filtered.apply(is_clustered, axis=1)]
analyze_df(train_filtered)








