# pylint: disable=E0401
# pylint: disable=E0602
import datetime
import logging
import os
import random
import traceback
from itertools import combinations
from typing import List

import pandas
import pandas as pd
import numpy as np
from pandas import DataFrame
from sklearn.ensemble import RandomForestClassifier
from sklearn.exceptions import UndefinedMetricWarning
from sklearn.metrics import precision_score
from sklearn.model_selection import train_test_split, RandomizedSearchCV, cross_val_score
from statsmodels.stats.outliers_influence import variance_inflation_factor
from tqdm import tqdm
from xgboost import XGBClassifier

from BL import DataProcessor
from BL.datatypes import TradeAction
from Connectors.dropbox_cache import DropBoxCache
from Connectors.tiingo import Tiingo, TradeType
from Predictors.deep_predictor import DeepPredictor
from Predictors.generic_predictor import GenericPredictor


class CombinationTrainer:

    def __init__(self, cache, indicators, predictor_store, test_mode):
        self._cache = cache
        self._indicators = indicators
        self._predictor_store = predictor_store
        self._target = "result"
        self._test_mode = test_mode

    @staticmethod
    def _filter_features_by_vif_and_precision(df, y, model, vif_threshold=5.0, cv_folds=5):
        """
        Entfernt Features mit hohem VIF und behält nur das Feature mit der höchsten Präzision.

        Parameters:
        - df: DataFrame mit Features.
        - y: Zielvariable (Pandas Series).
        - model: ML-Modell (muss `fit` und `score` oder `cross_val_score` unterstützen).
        - vif_threshold: Maximal erlaubter VIF-Wert.
        - cv_folds: Anzahl der Cross-Validation-Folds.

        Returns:
        - Bereinigter DataFrame mit den besten Features.
        """

        def calculate_vif(dataframe):
            """Berechnet die VIF-Werte für alle Features."""
            vif_data = pd.DataFrame()
            vif_data['Feature'] = dataframe.columns
            vif_data['VIF'] = [
                variance_inflation_factor(dataframe.values, i) for i in range(dataframe.shape[1])
            ]
            return vif_data

        df_filtered = df.copy()

        while True:
            vif_df = calculate_vif(df_filtered)
            high_vif_features = vif_df[vif_df['VIF'] > vif_threshold]['Feature'].tolist()

            if not high_vif_features:  # Keine Features mit hohem VIF mehr -> Abbruch
                break

            features_to_remove = set()
            for feature in high_vif_features:
                # Korrelationen berechnen
                correlated_features = df_filtered.corr()[feature].abs()
                correlated_features = correlated_features[correlated_features > 0.7].index.tolist()

                if len(correlated_features) > 1:
                    # Präzision für jedes Feature berechnen
                    precision_scores = {}
                    for f in correlated_features:
                        score = np.mean(cross_val_score(model, df_filtered[[f]], y, cv=cv_folds))
                        precision_scores[f] = score

                    # Bestes Feature auswählen
                    best_feature = max(precision_scores, key=precision_scores.get)
                    correlated_features.remove(best_feature)  # Alle außer das Beste entfernen
                    features_to_remove.update(correlated_features)

            # Falls sich nichts mehr verändert -> Abbruch
            if not features_to_remove:
                break

            # Entferne die ausgewählten Features
            df_filtered = df_filtered.drop(columns=features_to_remove)

        return df_filtered

    @staticmethod
    def _predict_sum(df, feature_cols, atr_factor_stop, atr_factor_limit):
        """
        Bewertet eine Feature-Kombination in einem Trading-DataFrame anhand von Precision und Reward.

        Args:
            df (pd.DataFrame): DataFrame mit Feature-Spalten (binär: 0/1) und einer 'result'-Spalte (0 = Verlust, 1 = Gewinn)
            feature_cols (List[str]): Liste von Spaltennamen, die alle 1 sein müssen, um einen Trade zu erzeugen
            atr_factor_stop (float): ATR-Faktor für Stop-Loss
            atr_factor_limit (float): ATR-Faktor für Take-Profit

        Returns:
            Tuple[float, float, List[int], int]:
                - Precision (gewichtete TP / (gewichtete TP + FP))
                - Reward (gewichtete TP - FP)
                - Liste der Indexe, an denen ein Trade stattfindet
                - Anzahl der Trades
        """
        import pandas as pd

        # Duplikate in Spalten prüfen
        #duplicated_columns = df.columns[df.columns.duplicated()].tolist()
        #if duplicated_columns:
        #    raise ValueError(f"Fehler: Doppelte Spalten im DataFrame gefunden: {duplicated_columns}")

        # Duplikate in feature_cols entfernen, Reihenfolge beibehalten
        feature_cols = list(dict.fromkeys(feature_cols))

        # Prüfen, ob alle Feature-Spalten im DataFrame vorhanden sind
        if not all(col in df.columns for col in feature_cols + ['result']):
            missing = [col for col in feature_cols + ['result'] if col not in df.columns]
            #print(f"Warnung: Fehlende Spalten: {missing}")
            return 0, 0, [], 0

        # Nur Zeilen, bei denen alle Features 1 sind
        trades = df[feature_cols].sum(axis=1) == len(feature_cols)

        # Berechne True Positives (TP) und False Positives (FP)
        TP = ((trades) & (df['result'] == 1)).sum()
        FP = ((trades) & (df['result'] == 0)).sum()

        # Verhältnis Take-Profit zu Stop-Loss
        atr_ratio = atr_factor_limit / atr_factor_stop

        # Gewichtete True Positives
        TP_scaled = TP * atr_ratio

        # Precision und Reward berechnen
        total = TP_scaled + FP
        precision = TP_scaled / total if total > 0 else 0
        reward = TP_scaled - FP

        # Indexe der getätigten Trades
        trade_indexes = df.index[trades].tolist()

        return precision, reward, trade_indexes, trades.sum()






    @staticmethod
    def _get_combos_by_best_features(num_features, best_features: List):
        combos = list(combinations(best_features, num_features))
        random.shuffle(combos)

        # Kürze die Liste auf 5 % der ursprünglichen Länge
        reduced_size = min(72000, int(len(combos)))  # Mindestens 1 Element behalten
        return combos[:reduced_size]

    @staticmethod
    def feature_importance_xgboost(df, target):
        """
        Berechnet die Feature-Wichtigkeit mit XGBoost.

        Args:
            df (pd.DataFrame): Der DataFrame mit den Features und der Zielspalte.
            target (str): Der Name der Zielspalte.

        Returns:
            pd.DataFrame: Ein DataFrame mit den Features und ihrer Wichtigkeit, absteigend sortiert.
        """
        # Trennen von Features und Zielvariable
        X = df.drop(columns=[target])
        y = df[target]

        # Initialisieren und Trainieren des XGBoost-Modells
        model = XGBClassifier(random_state=42, use_label_encoder=False, eval_metric='logloss')
        model.fit(X, y)

        # Abrufen der Feature-Wichtigkeiten
        importance = model.feature_importances_

        # Erstellen eines DataFrames mit den Feature-Wichtigkeiten
        importance_df = pd.DataFrame({'Feature': X.columns, 'Importance': importance})
        importance_df = importance_df.sort_values(by='Importance', ascending=False)

        return importance_df

    def train(self, df,
              min_prec_train: float,
              atr_factor_stop: float,
              trading_mode,
              atr_factor_limit: float,
              min_train_reward:int,
               combos: List = None):

        df = df.loc[:, ~df.columns.duplicated()]
        train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)
        # Doppelte Spalten im DataFrame entfernen

        results = []

        for features in combos:
            try:
                train_precision, train_reward, trade_indexes_train, trade_count_train = self._predict_sum(train_df,
                                                                                                          features,
                                                                                                          atr_factor_stop,
                                                                                                          atr_factor_limit)

                # Mindestbedingungen prüfen
                if train_precision >= min_prec_train:
                    if train_reward >= min_train_reward:
                        test_precision, test_reward, trade_indexes_test, trade_count_test = self._predict_sum(test_df,
                                                                                                              features,
                                                                                                              atr_factor_stop,
                                                                                                              atr_factor_limit)

                        results.append({
                            "_features": features,
                            "_train_precision": train_precision,
                            "_train_reward": train_reward,
                            "_test_precision": test_precision,
                            "_test_reward": test_reward,
                            "_trade_mode": trading_mode,
                            "_test_trade_count": trade_count_test,
                            "_unique_indexes": trade_indexes_test,
                        })



            except Exception as e:
                traceback_str = traceback.format_exc()
                print(f"Error: {e} with {features} {traceback_str}")

        df = DataFrame(results)
        if len(df) > 0:
            df = df[df["_test_trade_count"] != 0]
            df = df[df["_train_reward"] > min_train_reward]

            if len(df) == 0:
                print("No valid results")
                return df

            unique_indexes = set(index for sublist in df["_unique_indexes"] for index in sublist)
            print(f"Indexes {len(unique_indexes)}")
            print(f"Train Reward Mean {df['_train_reward'].mean()}")
            print(f"Test Reward Mean {df['_test_reward'].mean()}")
            print(f"Test Reward Median {df['_test_reward'].median()}")
            print(f"Test Reward Sum {df['_test_reward'].sum()}")
            print(f"Test Precision {df['_test_precision'].mean()}")
            print(f"Test Trade Count {df['_test_trade_count'].mean()}")

        return df

    def create_combos(self, best_features, existing_combos, num_features):
        # Kombis aus besten Features generieren
        combos = self._get_combos_by_best_features(num_features, best_features)
        if existing_combos is not None:
            combos = existing_combos + combos
        random.shuffle(combos)
        # Kürze die Liste auf 5 % der ursprünglichen Länge
        reduced_size = min(350000, int(len(combos)))  # Mindestens 1 Element behalten
        combos = combos[:reduced_size]
        return combos

    def create_data(self, tiingo, symbol, trade_type, data_processor, simulation, hours, factor_stop, factor_limit, indicators,
                    trade_mode: str,
                    cache) -> (DataFrame, DataFrame, str):
        df_train, eval_df_train = self._get_train_data(tiingo, symbol, trade_type, data_processor=data_processor,
                                                       dropbox_cache=cache)
        if len(df_train) < 500:
            raise Exception("Invalid data")

        buy_results, sell_results = simulation.simulate(df_train, eval_df_train, symbol,
                                                        time_frame=hours, factor_stop=factor_stop,
                                                        factor_limit=factor_limit)
        simulation.get_signals(symbol, df_train, indicators, GenericPredictor)
        train_signals_df = simulation.create_combined_indicator_data(indicators, symbol)
        trade_results = []
        pd.set_option('future.no_silent_downcasting', True)
        # Set specific replacement values for each trade type
        if trade_mode == TradeAction.BUY:
            train_signals_df = train_signals_df.replace({'none': 0, 'both': 1, 'buy': 1, 'sell': 0})
            trade_results = buy_results
        elif trade_mode == TradeAction.SELL:
            train_signals_df = train_signals_df.replace({'none': 0, 'both': 1, 'buy': 0, 'sell': 1})
            trade_results = sell_results

        # Prepare results data
        trade_results = trade_results[['chart_index', 'result']]
        trade_results['result'] = trade_results['result'].apply(lambda x: 1 if x > 0 else 0)
        signal_result_df = pd.merge(train_signals_df, trade_results, on='chart_index', how='left')
        signal_result_df['result'] = signal_result_df['result'].fillna(0)
        signal_result_df = signal_result_df.dropna()

        df = signal_result_df.drop(columns=["chart_index"])

        return df

    @staticmethod
    def _get_train_data(tiingo: Tiingo, symbol: str, trade_type: TradeType, data_processor: DataProcessor,
                        dropbox_cache: DropBoxCache) -> (DataFrame, DataFrame):
        hour_df = f"{symbol}_train_1hour_6.csv"
        day_df = f"{symbol}_train_1day_6.csv"

        if dropbox_cache.train_cache_exist(hour_df) and dropbox_cache.train_cache_exist(day_df):
            df_train = dropbox_cache.load_train_cache(hour_df)
            eval_df_train = dropbox_cache.load_train_cache(day_df)
        else:
            df_train, eval_df_train = tiingo.load_test_data(symbol, data_processor, trade_type=trade_type,
                                                            use_cache=True)
            dropbox_cache.save_train_cache(df_train, hour_df)
            dropbox_cache.save_train_cache(eval_df_train, day_df)

        df_train = df_train.astype({col: 'float32' for col in df_train.select_dtypes(include='float64').columns})
        eval_df_train = eval_df_train.astype(
            {col: 'float32' for col in eval_df_train.select_dtypes(include='float64').columns})
        return df_train, eval_df_train
