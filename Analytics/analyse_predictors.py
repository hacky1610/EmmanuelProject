import pandas as pd

import pandas as pd
from collections import Counter

from collections import Counter
import itertools

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
        '_test_trade_count': ['sum'],
    })

    # Spaltennamen flach machen
    summary.columns = ['_'.join(col).strip() for col in summary.columns.values]
    summary = summary.rename(columns={'_symbol_count': 'num_entries'})

    return summary
pd.set_option('display.max_columns', None)
df = pd.read_parquet("../predictor_3.parquet" )
print(df["_test_precision"].mean())
print(df["_test_reward"].mean())
print(df[df["_trade_mode"] == "sell"]["_test_precision"].mean())

most_common_combo(df)
most_common_features(df)

for f in [2.0,1.5,1.2,1.0,0.8]:

    print(f"Factor {f} - {df[df['_atr_factor_stop'] == f]['_test_precision'].mean()}")
#print(analyze_by_symbol(df))



