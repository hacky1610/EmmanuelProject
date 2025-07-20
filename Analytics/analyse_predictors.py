import pandas as pd
import statistics
import pandas as pd
from collections import Counter
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter
import itertools

import pandas as pd
import numpy as np
from itertools import product

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import norm

def trade_distance_variance(indexes):
    if isinstance(indexes, list) and len(indexes) >= 2:
        diffs = [j - i for i, j in zip(indexes[:-1], indexes[1:])]
        return pd.Series(diffs).var()
    return 0

def wilson_score(p, n, z=1.96):
    if n == 0:
        return 0
    denominator = 1 + z**2 / n
    centre_adj = p + z*z / (2*n)
    adj_stddev = np.sqrt((p*(1 - p) + z*z / (4*n)) / n)
    return (centre_adj - z*adj_stddev) / denominator

def analyze_issues(df):
    print("=== Erweiterte Analyse potenzieller Schwächen ===")

    df = df.copy()

    # Gaps
    df['precision_gap'] = df['_train_precision'] - df['_test_precision']
    df['reward_gap'] = df['_train_reward'] - df['_test_reward']

    print(f"\n--- Overfitting-Indikatoren ---")
    print(f"Ø Precision-Gap: {df['precision_gap'].mean():.2f}")
    print(f"Strategien mit GAP > 0.5: {(df['precision_gap'] > 0.5).sum()}")

    few_trades = df[df['_test_trade_count'] < 4]
    print(f"\n--- Wenig Test-Trades ---")
    print(f"Strategien mit < 4 Test-Trades: {len(few_trades)}")
    print(f"Ø Test-Precision dieser Strategien: {few_trades['_test_precision'].mean():.2f}")

    df['_test_variance_calc'] = df['_test_indexes'].apply(trade_distance_variance)
    clustered = df[(df['_test_trade_count'] > 5) & (df['_test_variance_calc'] < 50)]
    print(f"\n--- Cluster-Trades ---")
    print(f"Strategien mit Trade-Cluster: {len(clustered)}")
    print(f"Ø Test-Precision (Cluster): {clustered['_test_precision'].mean():.2f}")

    df['features_len'] = df['_features'].apply(len)
    complexity = df.groupby('features_len')['_test_precision'].agg(['mean', 'count'])
    print(f"\n--- Feature-Komplexität ---\n{complexity}")

    df['test_confidence'] = df.apply(
        lambda row: wilson_score(row['_test_precision'], row['_test_trade_count']), axis=1
    )
    low_conf = df[df['test_confidence'] < 0.4]
    print(f"\n--- Niedrige Konfidenz (Wilson < 0.4) ---")
    print(f"Strategien mit niedriger Konfidenz: {len(low_conf)}")
    print(f"Ø Test-Precision dieser Strategien: {low_conf['_test_precision'].mean():.2f}")

    print(f"\n--- Symbol-Qualität ---")
    symbol_stats = df.groupby('_symbol')['_test_precision'].agg(['mean', 'count']).sort_values('mean')
    print(symbol_stats.head(5))

    bad_profit = df[(df['_test_precision'] > 0.6) & (df['_test_reward'] < 0)]
    print(f"\n--- Gute Precision, aber Verlust ---")
    print(bad_profit[['features_len', '_test_precision', '_test_reward', '_test_trade_count']].head())

    # Visualisierung
    df['reward_per_trade'] = df['_test_reward'] / df['_test_trade_count'].replace(0, 1)
    df.plot.scatter(x='_test_precision', y='reward_per_trade', alpha=0.3, title='Reward/Trade vs. Test Precision')
    plt.tight_layout()
    plt.show()

    df['_test_reward'].hist(bins=50, grid=False, alpha=0.7)
    plt.title("Verteilung der Test-Rewards")
    plt.xlabel("Reward")
    plt.ylabel("Anzahl Strategien")
    plt.show()

    # === Erweiterung: Top-Strategien mit hoher Konfidenz und hohem Reward ===
    top_strategies = df[
        (df['test_confidence'] > 0.6) &
        (df['_test_reward'] > 5) &
        (df['_test_trade_count'] >= 5)
    ].sort_values('test_confidence', ascending=False).head(10)

    print("\n--- Top Strategien (hoch konfid., guter Reward) ---")
    for i, row in top_strategies.iterrows():
        print(f"Prec={row._test_precision:.2f} Reward={row._test_reward:.2f} Trades={row._test_trade_count} Conf={row.test_confidence:.2f} Features={len(row._features)}")

    # === Erweiterung: Ausreißer mit hoher Precision aber schlechtem Reward ===
    reward_outliers = df[(df['_test_precision'] > 0.7) & (df['_test_reward'] < -5)]
    print(f"\n--- Ausreißer: Hohe Precision, aber klarer Verlust --- ({len(reward_outliers)})")
    if not reward_outliers.empty:
        print(reward_outliers[['features_len', '_test_precision', '_test_reward', '_symbol']].head())

    print(f"\n=== Analyse abgeschlossen ({len(df)} Strategien) ===")



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

def is_clustered(row, min_variance=80, min_span=200, max_density=0.1):
    indexes = row['_train_indexes']
    if indexes is None or len(indexes) < 2:
        return True

    span = max(indexes) - min(indexes)
    density = row['_train_trade_count'] / span if span > 0 else float('inf')

    return row['_train_variance'] < min_variance or span < min_span or density > max_density


def analyze_df(df, show_plots=True, top_n=5):
    print("=== Gesamtmetriken ===")
    print(f"Ø Test Precision:     {(df['_test_precision'] * 100).mean():.2f} %")
    print(f"Ø Test Reward:        {df['_test_reward'].mean():.2f}")
    print(f"Ø Test Precision (sell): {df[df['_trade_mode'] == 'sell']['_test_precision'].mean():.2f}")
    print(f"Anzahl Strategien:    {len(df)}\n")

    print("=== Meistverwendete Features ===")
    most_common_features(df)  # bleibt wie gehabt
    print()

    print("=== Testmetriken pro ATR-Faktor-Kombi ===")
    for _, row in df[["_atr_factor_stop", "_atr_factor_limit"]].drop_duplicates().iterrows():
        stop = row["_atr_factor_stop"]
        limit = row["_atr_factor_limit"]
        subset = df[(df["_atr_factor_stop"] == stop) & (df["_atr_factor_limit"] == limit)]
        print(f"ATR {stop}/{limit} → Precision: {subset['_test_precision'].mean():.2f}, Reward: {subset['_test_reward'].mean():.2f}")
    print()

    print("=== Metriken pro Symbol ===")
    symbols = df["_symbol"].unique()
    sum_prec = 0
    for symbol in symbols:
        symbol_df = df[df["_symbol"] == symbol]
        prec = symbol_df["_test_precision"].mean()
        reward = symbol_df["_test_reward"].mean()
        sum_prec += prec
        print(f"{symbol}: Precision={prec:.2f}, Reward={reward:.2f}, Count={len(symbol_df)}")
    print(f"\nGesamtdurchschnitt Precision über Symbole: {sum_prec / len(symbols):.2f}\n")

    print("=== Metriken nach Anzahl Features ===")
    df['features_len'] = df['_features'].apply(len)
    for f_len in sorted(df["features_len"].unique()):
        sub = df[df['features_len'] == f_len]
        print(f"{f_len} Features → Precision={sub['_test_precision'].mean():.2f}, Reward={sub['_test_reward'].mean():.2f}, Count={len(sub)}")
    print()

    # Top / Flop Strategien
    print("=== Top/Flop Strategien ===")
    top = df.sort_values(by="_test_precision", ascending=False).head(top_n)
    flop = df.sort_values(by="_test_precision", ascending=True).head(top_n)

    print("\nTop Strategien:")
    for i, row in top.iterrows():
        print(f"Prec={row['_test_precision']:.2f}  Reward={row['_test_reward']:.2f}  Features={row['features_len']}  Trades={row['_test_trade_count']}")

    print("\nFlop Strategien:")
    for i, row in flop.iterrows():
        print(f"Prec={row['_test_precision']:.2f}  Reward={row['_test_reward']:.2f}  Features={row['features_len']}  Trades={row['_test_trade_count']}")
    print()

    # Optionale Plots
    if show_plots:
        print("=== Verteilungen ===")
        fig, axes = plt.subplots(1, 3, figsize=(15, 4))
        df['_test_precision'].hist(ax=axes[0], bins=20)
        axes[0].set_title("Test Precision")

        df['_test_reward'].hist(ax=axes[1], bins=20)
        axes[1].set_title("Test Reward")

        df['_train_variance'].hist(ax=axes[2], bins=20)
        axes[2].set_title("Train Variance")

        plt.tight_layout()
        plt.show()

pd.set_option('display.max_columns', None)
df = pd.read_parquet("/home/daniel/Documents/Projects/predictor_5.parquet" )

df = df[
    ~(
        (df["_atr_factor_stop"] == 1.2) &
        (df["_atr_factor_limit"] == 1.8)
    )
]
df.to_parquet("../predictor_5.parquet" )

def wilson_score(p, n, z=1.96):  # z=1.96 für 95% Konfidenz
    if n == 0:
        return 0
    denominator = 1 + z**2 / n
    centre = p + z**2 / (2 * n)
    margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n)
    return (centre - margin) / denominator

def analyze_wilson(df):
    print("\n=== Wilson-Score Analyse ===")

    # Überblick
    print(f"Ø Wilson-Score: {df['wilson_score'].mean():.2f}")
    print(f"Max. Wilson-Score: {df['wilson_score'].max():.2f}")
    print(f"Min. Wilson-Score: {df['wilson_score'].min():.2f}")

    # Gruppenweise Verteilung
    thresholds = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]
    for t in thresholds:
        count = len(df[df['wilson_score'] >= t])
        prec = df[df['wilson_score'] >= t]['_test_precision'].mean()
        reward = df[df['wilson_score'] >= t]['_test_reward'].mean()
        print(f"WS ≥ {t:.1f}: {count} Strategien, Ø Precision={prec:.2f}, Ø Reward={reward:.2f}")

    # Wilson vs. Test Precision visualisieren
    try:
        import seaborn as sns
        import matplotlib.pyplot as plt
        sns.set(style="whitegrid")
        plt.figure(figsize=(8, 5))
        sns.scatterplot(data=df, x='wilson_score', y='_test_precision', hue='_test_trade_count', palette='coolwarm', alpha=0.6)
        plt.title("Wilson-Score vs Test Precision")
        plt.xlabel("Wilson Score")
        plt.ylabel("Test Precision")
        plt.legend(title='Trade Count', loc='lower right')
        plt.tight_layout()
        plt.show()
    except Exception as e:
        print(f"Plot konnte nicht erstellt werden: {e}")


def analyse_trade_index_distribution(indexes, max_cluster_gap=2, outlier_thresh=100):
    if not isinstance(indexes, np.ndarray) or len(indexes) < 2:
        return pd.Series({
            'cluster_count': np.nan,
            'max_cluster_size': np.nan,
            'outlier_count': np.nan
        })

    indexes = np.sort(indexes)
    diffs = np.diff(indexes)

    cluster_sizes = []
    current_cluster = 1

    for diff in diffs:
        if diff <= max_cluster_gap:
            current_cluster += 1
        else:
            # Cluster mit mindestens 2 Elementen speichern
            if current_cluster >= 2:
                cluster_sizes.append(current_cluster)
            current_cluster = 1  # Neuer möglicher Cluster

    # Letzter Cluster ggf. hinzufügen
    if current_cluster >= 2:
        cluster_sizes.append(current_cluster)

    outlier_count = np.sum(diffs > outlier_thresh)

    return pd.Series({
        'cluster_count': len(cluster_sizes),
        'max_cluster_size': max(cluster_sizes) if cluster_sizes else 0,
        'outlier_count': int(outlier_count)
    })



def analyze_span_density(df):
    print("\n=== Analyse: Train Span & Train Density ===")

    print(f"Anzahl Strategien: {len(df)}")
    print(f"Ø Train Span (h): {df['train_span'].mean():.2f}")
    print(f"Ø Train Density (trades/span): {df['train_density'].mean():.4f}")
    print(f"Min Span: {df['train_span'].min()}, Max Span: {df['train_span'].max()}")
    print(f"Min Density: {df['train_density'].min():.4f}, Max Density: {df['train_density'].max():.4f}")

    # Gruppieren nach Dichte
    bins = [0, 0.05, 0.1, 0.2, 0.5, 1.0]
    labels = ["≤0.05", "0.05–0.1", "0.1–0.2", "0.2–0.5", ">0.5"]
    df['density_group'] = pd.cut(df['train_density'], bins=bins, labels=labels, include_lowest=True)

    print("\n--- Ø Test-Precision nach Density-Gruppe ---")
    precision_by_group = df.groupby('density_group')['_test_precision'].agg(['mean', 'count']).reset_index()
    print(precision_by_group)

    print("\n--- Ø Train-Span nach Density-Gruppe ---")
    span_by_group = df.groupby('density_group')['train_span'].agg(['mean', 'count']).reset_index()
    print(span_by_group)

    # Optional visualisieren (wenn gewünscht):
    # import seaborn as sns
    # import matplotlib.pyplot as plt
    # sns.boxplot(data=df, x='density_group', y='_test_precision')
    # plt.show()


def analyze_worst_strategies(df, n=10):
    print(f"\n=== Analyse der {n} Strategien mit dem schlechtesten Test-Reward ===")

    # Schlechteste Strategien nach Test-Reward
    worst_strategies = df.sort_values('_test_reward').head(n)

    for idx, row in worst_strategies.iterrows():
        print(f"\n--- Strategie #{idx} ---")
        print(f"Test-Precision: {row['_test_precision']:.2f}")
        print(f"Test-Reward:    {row['_test_reward']:.2f}")
        print(f"Test-Trades:    {row['_test_trade_count']}")
        print(f"Wilson-Score:   {row['wilson_score']:.2f}")
        print(f"Train-Precision: {row['_train_precision']:.2f}")
        print(f"Train-Reward:    {row['_train_reward']:.2f}")
        print(f"Symbol:         {row['_symbol']}")
        print(f"Trade Mode:     {row.get('_trade_mode', 'N/A')}")
        print(f"Features ({len(row['_features'])}): {row['_features']}")

        # Indexliste der Test-Trades
        # Indexliste der Test-Trades
        print(f"Train-Trade-Indexes: {row['_train_indexes']}")

        # Optional: Dichte & Verteilung der Testtrades
        if row['_train_trade_count'] > 1:
            diffs = [j - i for i, j in zip(row['_train_indexes'][:-1], row['_train_indexes'][1:])]
            print(f"  Abstand zw. Trades (Stunden): {diffs}")
            print(f"  Ø Abstand: {np.mean(diffs):.2f}, Varianz: {np.var(diffs):.2f}")
        else:
            print("  Nur 1 Train-Trade vorhanden.")

import numpy as np

def calculate_index_distances(indexes):
    if isinstance(indexes, list) and len(indexes) >= 2:
        diffs = np.diff(sorted(indexes))
        return pd.Series({
            'train_index_median_distance': np.median(diffs),
            'train_index_mean_distance': np.mean(diffs),
            'train_index_variance_distance': np.var(diffs)
        })
    return pd.Series({
        'train_index_median_distance': np.nan,
        'train_index_mean_distance': np.nan,
        'train_index_variance_distance': np.nan
    })

def identify_strategies_with_cluster_problems(df, cluster_thresh=5, outlier_thresh=2):
    cluster_issues = df[(df['max_cluster_size'] > cluster_thresh) | (df['outlier_count'] > outlier_thresh)]
    print(f"\n=== Strategien mit Cluster- oder Outlier-Problemen: {len(cluster_issues)} ===")
    if not cluster_issues.empty:
        print(cluster_issues[['_symbol', 'cluster_count', 'max_cluster_size', 'outlier_count']].head(20))
    return cluster_issues

def identify_problematic_strategies(df, median_thresh=5, var_thresh=100, reward_thresh=0):
    print("\n=== Analyse: Problematische Strategien ===")

    clustered = df[df['train_index_median_distance'] < median_thresh]
    print(f"⚠️ Strategien mit Median-Abstand < {median_thresh}: {len(clustered)}")

    high_precision_low_reward = df[(df['_test_precision'] > 0.7) & (df['_test_reward'] < reward_thresh)]
    print(f"⚠️ Strategien mit hoher Precision, aber Reward ≤ {reward_thresh}: {len(high_precision_low_reward)}")

    high_variance = df[df['train_index_variance_distance'] > var_thresh]
    print(f"⚠️ Strategien mit Varianz der Abstände > {var_thresh}: {len(high_variance)}")

    # Details (optional):
    if not clustered.empty:
        print("\n--- Cluster-Gefahr (geringer Median-Abstand) ---")
        print(clustered[['_symbol', '_test_precision', '_test_reward', 'train_index_median_distance']].head())

    if not high_precision_low_reward.empty:
        print("\n--- Hohe Präzision, schlechter Reward ---")
        print(high_precision_low_reward[
                  ['_symbol', '_test_precision', '_test_reward', 'train_index_median_distance']].head())

    if not high_variance.empty:
        print("\n--- Hohe Varianz der Abstände ---")
        print(high_variance[['_symbol', '_test_precision', '_test_reward', 'train_index_variance_distance']].head())

def analyse_precision_by_bins(df, precision_col='_test_precision'):
    result = {}

    # Definition der Bins für jede Spalte
    binning_config = {
        'cluster_count': [0, 5, 10, 20, 999],
        'max_cluster_size': [0, 3, 7, 14, 999],
        'outlier_count': [0, 1, 3, 5, 999],
    }

    for feature, bins in binning_config.items():
        labels = [f"{bins[i]}–{bins[i+1]-1}" if bins[i+1] != 999 else f"{bins[i]}+" for i in range(len(bins)-1)]
        binned = pd.cut(df[feature], bins=bins, labels=labels, include_lowest=True)
        grouped = df.groupby(binned)[precision_col].mean().round(3)
        result[feature] = grouped

    # Übersicht anzeigen
    for feature, grouped in result.items():
        print(f"\n=== ⏹️ {feature} → Ø _test_precision pro Bin ===")
        print(grouped)

    return result

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


filtered_df = df[
    (df['_train_precision'] > 0.66)
]


def add_measure_parameters(df):
    new_df = df.copy()
    new_df['train_span'] = new_df['_train_indexes'].apply(lambda x: max(x) - min(x))
    new_df['train_density'] = new_df['_train_trade_count'] / new_df['train_span']
    new_df[['cluster_count', 'max_cluster_size', 'outlier_count']] = new_df['_train_indexes'].apply(
        lambda x: analyse_trade_index_distribution(x)
    )
    new_df['test_confidence'] = new_df.apply(
        lambda row: wilson_score(row['_test_precision'], row['_test_trade_count']),
        axis=1
    )
    new_df[[
        'train_index_median_distance',
        'train_index_mean_distance',
        'train_index_variance_distance'
    ]] = new_df['_train_indexes'].apply(calculate_index_distances)
    new_df['wilson_score'] = new_df.apply(
        lambda row: wilson_score(row['_test_precision'], row['_test_trade_count']), axis=1)

    return new_df


filtered_df = add_measure_parameters(filtered_df)

schlechte_symbole = ['NZDCAD', 'EURNZD', 'USDCAD', 'USDSGD', "USDJPY", "EURAUD", "GBPNZD",
                     'AUDUSD', 'NZDUSD', 'EURUSD', 'EURCAD', 'USDHKD']
filtered_df = filtered_df[~filtered_df['_symbol'].isin(schlechte_symbole)]
df_filtered = filtered_df[
    (filtered_df['cluster_count'].between(5, 19)) &
    (filtered_df['max_cluster_size'] <= 6)
]
df_filtered = df_filtered[df_filtered['features_len'].between(5, 8)]
df_filtered = df_filtered[df_filtered.wilson_score >= 0.4]


filtered_df = filtered_df[~filtered_df.apply(is_clustered, axis=1)]
analyze_df(filtered_df)
analyze_issues(filtered_df)
analyze_span_density(filtered_df)
analyze_worst_strategies(filtered_df)
identify_problematic_strategies(filtered_df)
identify_strategies_with_cluster_problems(filtered_df)
analyse_precision_by_bins(filtered_df)






