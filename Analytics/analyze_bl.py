import itertools
from collections import Counter

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt


class AnalyzeParamCreator():

    def add_measure_parameters(self,df):
        new_df = df.copy()
        new_df['train_span'] = new_df['_train_indexes'].apply(lambda x: max(x) - min(x))
        new_df['train_density'] = new_df['_train_trade_count'] / new_df['train_span']
        new_df[['cluster_count', 'max_cluster_size', 'cluster_size_median', 'outlier_count']] = new_df['_train_indexes'].apply(
            lambda x: self._analyse_trade_index_distribution(x)
        )
        new_df['_test_variance_calc'] = new_df['_test_indexes'].apply(self._trade_distance_variance)

        new_df['test_confidence'] = new_df.apply(
            lambda row: self._wilson_score(row['_test_precision'], row['_test_trade_count']),
            axis=1
        )

        new_df[[
            'train_index_median_distance',
            'train_index_mean_distance',
            'train_index_variance_distance'
        ]] = new_df['_train_indexes'].apply(self._calculate_index_distances)
        new_df['wilson_score'] = new_df['test_confidence']

        return new_df

    @staticmethod
    def _trade_distance_variance(indexes):
        if isinstance(indexes, list) and len(indexes) >= 2:
            diffs = [j - i for i, j in zip(indexes[:-1], indexes[1:])]
            return pd.Series(diffs).var()
        return 0

    @staticmethod
    def _analyse_trade_index_distribution(indexes, max_cluster_gap=2, outlier_thresh=100):
        if not isinstance(indexes, (list, np.ndarray)) or len(indexes) == 0:
            return pd.Series({
                'cluster_count': 0,
                'max_cluster_size': 0,
                'cluster_size_median': 0,
                'outlier_count': 0
            })

        indexes = np.sort(indexes)
        diffs = np.diff(indexes)

        cluster_sizes = []
        current_cluster = 1

        for diff in diffs:
            if diff <= max_cluster_gap:
                current_cluster += 1
            else:
                cluster_sizes.append(current_cluster)
                current_cluster = 1

        # letzten Cluster hinzufügen
        cluster_sizes.append(current_cluster)

        outlier_count = np.sum(diffs > outlier_thresh)

        return pd.Series({
            'cluster_count': len(cluster_sizes),
            'max_cluster_size': max(cluster_sizes),
            'cluster_size_median': float(np.median(cluster_sizes)),
            'outlier_count': int(outlier_count)
        })

    @staticmethod
    def _wilson_score(p, n, z=1.96):
        if n == 0:
            return 0
        denominator = 1 + z ** 2 / n
        centre_adj = p + z * z / (2 * n)
        adj_stddev = np.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
        return (centre_adj - z * adj_stddev) / denominator

    @staticmethod
    def _calculate_index_distances(indexes):
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


class Analyzer():

    def analyze(self, df):
        self._analyze_df(df)
        self._analyze_issues(df)
        self._analyze_span_density(df)
        self._analyze_worst_strategies(df)
        self._identify_problematic_strategies(df)
        self._identify_strategies_with_cluster_problems(df)
        self._analyse_precision_by_bins(df)


    def find_best_filter_combination(self, df, min_precision=0.65, min_strategies=5):
        # Parameterbereiche, die wir permutieren
        cluster_size_medians = [1, 2]
        max_cluster_sizes = [2, 3, 4, 5, 6]
        outlier_counts = [0, 1, 2]
        min_trade_counts = [5, 6, 7]
        max_feature_lens = [5, 6, 7]

        best_result = {
            'mean_precision': 0,
            'count': 0,
            'params': None,
            'filtered_df': None
        }

        # Alle Kombinationen durchprobieren
        for comb in itertools.product(cluster_size_medians, max_cluster_sizes, outlier_counts, min_trade_counts,
                                      max_feature_lens):
            cluster_median, cluster_max, outliers, trade_min, feature_max = comb

            filtered_df = df[
                (df['cluster_size_median'] <= cluster_median) &
                (df['max_cluster_size'] <= cluster_max) &
                (df['outlier_count'] <= outliers) &
                (df['_test_trade_count'] >= trade_min) &
                (df['features_len'] <= feature_max)
                ]

            if len(filtered_df) >= min_strategies:
                mean_precision = filtered_df['_test_precision'].mean()
                if mean_precision >= min_precision and len(filtered_df) > best_result['count']:
                    best_result = {
                        'mean_precision': mean_precision,
                        'count': len(filtered_df),
                        'params': {
                            'cluster_size_median': cluster_median,
                            'max_cluster_size': cluster_max,
                            'outlier_count': outliers,
                            '_test_trade_count ≥': trade_min,
                            'features_len ≤': feature_max
                        },
                        'filtered_df': filtered_df
                    }

        return best_result

    def _analyze_span_density(self,df):
        print("\n=== Analyse: Train Span & Train Density ===")

        print(f"Anzahl Strategien: {len(df)}")
        print(f"Ø Train Span (h): {df['train_span'].mean():.2f}")
        print(f"Ø Train Density (trades/span): {df['train_density'].mean():.4f}")
        print(f"Min Span: {df['train_span'].min()}, Max Span: {df['train_span'].max()}")
        print(f"Min Density: {df['train_density'].min():.4f}, Max Density: {df['train_density'].max():.4f}")

        # Gruppieren nach Dichte
        bins = [0, 0.05, 0.1, 0.2, 0.5, 1.0]
        labels = ["≤0.05", "0.05–0.1", "0.1–0.2", "0.2–0.5", ">0.5"]
        df = df.copy()
        df['density_group'] = pd.cut(df['train_density'], bins=bins, labels=labels, include_lowest=True)

        print("\n--- Ø Test-Precision nach Density-Gruppe ---")
        precision_by_group = df.groupby('density_group', observed=True)['_test_precision'].agg(['mean', 'count']).reset_index()
        print(precision_by_group)

        print("\n--- Ø Train-Span nach Density-Gruppe ---")
        span_by_group = df.groupby('density_group', observed=True)['train_span'].agg(['mean', 'count']).reset_index()
        print(span_by_group)

        # Optional visualisieren (wenn gewünscht):
        # import seaborn as sns
        # import matplotlib.pyplot as plt
        # sns.boxplot(data=df, x='density_group', y='_test_precision')
        # plt.show()

    @staticmethod
    def _analyze_issues(df):
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

        if "_test_variance_calc" in df.columns:
            clustered = df[(df['_test_trade_count'] > 5) & (df['_test_variance_calc'] < 50)]
            print(f"\n--- Cluster-Trades ---")
            print(f"Strategien mit Trade-Cluster: {len(clustered)}")
            print(f"Ø Test-Precision (Cluster): {clustered['_test_precision'].mean():.2f}")

        df['features_len'] = df['_features'].apply(len)
        complexity = df.groupby('features_len')['_test_precision'].agg(['mean', 'count'])
        print(f"\n--- Feature-Komplexität ---\n{complexity}")


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

        # === Erweiterung: Top-Strategien mit hoher Konfidenz und hohem Reward ===
        top_strategies = df[
            (df['test_confidence'] > 0.6) &
            (df['_test_reward'] > 5) &
            (df['_test_trade_count'] >= 5)
            ].sort_values('test_confidence', ascending=False).head(10)

        print("\n--- Top Strategien (hoch konfid., guter Reward) ---")
        for i, row in top_strategies.iterrows():
            print(
                f"Prec={row._test_precision:.2f} Reward={row._test_reward:.2f} Trades={row._test_trade_count} Conf={row.test_confidence:.2f} Features={len(row._features)}")

        # === Erweiterung: Ausreißer mit hoher Precision aber schlechtem Reward ===
        reward_outliers = df[(df['_test_precision'] > 0.7) & (df['_test_reward'] < -5)]
        print(f"\n--- Ausreißer: Hohe Precision, aber klarer Verlust --- ({len(reward_outliers)})")
        if not reward_outliers.empty:
            print(reward_outliers[['features_len', '_test_precision', '_test_reward', '_symbol']].head())

        print(f"\n=== Analyse abgeschlossen ({len(df)} Strategien) ===")

    @staticmethod
    def _analyze_worst_strategies(df, n=10):
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

    def _analyze_df(self, df, show_plots=False, top_n=5):
        print("=== Gesamtmetriken ===")
        print(f"Ø Test Precision:     {(df['_test_precision'] * 100).mean():.2f} %")
        print(f"Ø Test Reward:        {df['_test_reward'].mean():.2f}")
        print(f"Ø Test Precision (sell): {df[df['_trade_mode'] == 'sell']['_test_precision'].mean():.2f}")
        print(f"Anzahl Strategien:    {len(df)}\n")

        print("=== Meistverwendete Features ===")
        self._most_common_features(df)  # bleibt wie gehabt
        print()

        print("=== Testmetriken pro ATR-Faktor-Kombi ===")
        for _, row in df[["_atr_factor_stop", "_atr_factor_limit"]].drop_duplicates().iterrows():
            stop = row["_atr_factor_stop"]
            limit = row["_atr_factor_limit"]
            subset = df[(df["_atr_factor_stop"] == stop) & (df["_atr_factor_limit"] == limit)]
            print(
                f"ATR {stop}/{limit} → Precision: {subset['_test_precision'].mean():.2f}, Reward: {subset['_test_reward'].mean():.2f}")
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
        df = df.copy()
        df['features_len'] = df['_features'].apply(len)
        for f_len in sorted(df["features_len"].unique()):
            sub = df[df['features_len'] == f_len]
            print(
                f"{f_len} Features → Precision={sub['_test_precision'].mean():.2f}, Reward={sub['_test_reward'].mean():.2f}, Count={len(sub)}")
        print()

        # Top / Flop Strategien
        print("=== Top/Flop Strategien ===")
        top = df.sort_values(by="_test_precision", ascending=False).head(top_n)
        flop = df.sort_values(by="_test_precision", ascending=True).head(top_n)

        print("\nTop Strategien:")
        for i, row in top.iterrows():
            print(
                f"Prec={row['_test_precision']:.2f}  Reward={row['_test_reward']:.2f}  Features={row['features_len']}  Trades={row['_test_trade_count']}")

        print("\nFlop Strategien:")
        for i, row in flop.iterrows():
            print(
                f"Prec={row['_test_precision']:.2f}  Reward={row['_test_reward']:.2f}  Features={row['features_len']}  Trades={row['_test_trade_count']}")
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

    @staticmethod
    def _most_common_features(df):
        # Alle Listen in eine einzige lange Liste zusammenführen
        all_features = list(itertools.chain.from_iterable(df['_features']))

        # Zählen, wie oft jedes einzelne Feature vorkommt
        feature_counts = Counter(all_features)

        # Die 15 häufigsten Features
        top_15 = feature_counts.most_common(15)

        # Ausgabe
        for i, (feature, count) in enumerate(top_15, 1):
            print(f"{i:2d}. {feature} → {count}x")

    def _most_common_combo(self,df):
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

    @staticmethod
    def _identify_strategies_with_cluster_problems(df, cluster_thresh=5, outlier_thresh=2):
        cluster_issues = df[(df['max_cluster_size'] > cluster_thresh) | (df['outlier_count'] > outlier_thresh)]
        print(f"\n=== Strategien mit Cluster- oder Outlier-Problemen: {len(cluster_issues)} ===")
        if not cluster_issues.empty:
            print(cluster_issues[['_symbol', 'cluster_count', 'max_cluster_size', 'outlier_count']].head(20))
        return cluster_issues

    @staticmethod
    def _identify_problematic_strategies(df, median_thresh=5, var_thresh=100, reward_thresh=0):
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

    @staticmethod
    def _analyse_precision_by_bins(df, precision_col='_test_precision'):
        result = {}

        # Definition der Bins für jede Spalte
        binning_config = {
            'cluster_count': [0, 5, 10, 20, 999],
            'max_cluster_size': [0, 3, 7, 14, 999],
            'cluster_size_median': [0,3,7,14,999],
            'outlier_count': [0, 1, 3, 5, 999],
        }

        for feature, bins in binning_config.items():
            labels = [f"{bins[i]}–{bins[i + 1] - 1}" if bins[i + 1] != 999 else f"{bins[i]}+" for i in
                      range(len(bins) - 1)]
            binned = pd.cut(df[feature], bins=bins, labels=labels, include_lowest=True)
            grouped = df.groupby(binned, observed=True)[precision_col].mean().round(3)
            result[feature] = grouped

        # Übersicht anzeigen
        for feature, grouped in result.items():
            print(f"\n=== ⏹️ {feature} → Ø _test_precision pro Bin ===")
            print(grouped)

        return result




