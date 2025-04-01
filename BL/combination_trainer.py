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

    def _predict(self, df: DataFrame, features: List[str], model: object, threshold: float) -> (float, int):

        x_test = df[list(features)]
        y_test = df[self._target]

        y_prob_test = model.predict_proba(x_test)[:, 1]
        y_pred_test = (y_prob_test >= threshold).astype(int)

        test_precision = precision_score(y_test, y_pred_test, zero_division=0)
        test_true_positives = ((y_pred_test == 1) & (y_test == 1)).sum()
        test_false_positives = ((y_pred_test == 1) & (y_test == 0)).sum()
        test_reward = test_true_positives - test_false_positives

        return test_precision, test_reward

    @staticmethod
    def _predict_sum(df, feature_cols, atr_factor_stop, atr_factor_limit):
        # Fälle, in denen alle Features 1 sind
        trades = df[list(feature_cols)].sum(axis=1) == len(feature_cols)

        # Berechnung von TP und FP
        TP = ((trades) & (df['result'] == 1)).sum()
        FP = ((trades) & (df['result'] == 0)).sum()

        # Berechnung des ATR-Verhältnisses
        atr_ratio = atr_factor_limit / atr_factor_stop

        # Nur die True Positives skalieren
        TP_scaled = TP * atr_ratio  # Skaliere die True Positives

        # Precision ist weiterhin die Standard-Precision (True Positives / (True Positives + False Positives))
        total = TP_scaled + FP
        precision = TP_scaled / total if total > 0 else 0

        # Reward ist die Differenz von TP und FP, aber skaliere nur TP
        reward = TP_scaled - FP

        # Liste der Indizes, an denen ein Trade gemacht wurde
        trade_indexes = df.index[trades].tolist()

        return precision, reward, trade_indexes, trades.sum()

    def _save_predictor(self, symbol: str, trade_mode: str,
                        trading_hours: int, features: List,
                        test_reward: int,
                        train_reward: int,
                        train_trade_count: int,
                        atr_factor_stop: float, atr_factor_limit: float,
                        test_precision: float,
                        train_precision: float,
                        test_trade_count: int, unique_indexes: int):
        dp = DeepPredictor(symbol=symbol, cache=self._cache,
                           indicators=self._indicators, config={})
        dp.set_model_params(trade_mode=trade_mode,
                            trading_hours=trading_hours,
                            features=list(features),
                            atr_factor_limit=atr_factor_limit,
                            atr_factor_stop=atr_factor_stop,
                            test_reward=test_reward, test_precision=test_precision,
                            test_trade_count=test_trade_count, unique_indexes=unique_indexes,
                            train_reward=train_reward,
                            train_precision=train_precision,
                            train_trade_count=train_trade_count
                            )
        self._predictor_store.save(dp)

    def _best_feature_pair_by_reward(self, df: DataFrame, symbol: str,
                                     trading_hours: int, trade_mode: str,
                                     num_features: int, atr_factor_stop: float,
                                     atr_factor_limit: float,
                                     min_prec_train: float, min_prec_test: float, best_features: list,
                                     part:float,
                                     existing_combos: List = None) -> DataFrame:

        train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)

        results = []
        # Kombis aus besten Features generieren
        combos = self._get_combos_by_best_features(num_features, best_features, part)

        if existing_combos is not None:
            combos = existing_combos + combos


        for features in tqdm(combos):
            try:
                train_precision, train_reward, trade_indexes_train, trade_count_train = self._predict_sum(train_df,
                                                                                                          features,atr_factor_stop,atr_factor_limit)

                # Mindestbedingungen prüfen
                if train_precision >= min_prec_train and train_reward >= 35:
                    test_precision, test_reward, trade_indexes_test, trade_count_test = self._predict_sum(test_df,
                                                                                                          features,atr_factor_stop,atr_factor_limit)

                    results.append({
                        "Features": features,
                        "Train Precision": train_precision,
                        "Train Reward": train_reward,
                        "Test Precision": test_precision,
                        "Test Reward": test_reward,
                        "Test Trade Count": trade_count_test,
                        "Test Indexes": trade_indexes_test,
                    })

            except Exception as e:
                traceback_str = traceback.format_exc()
                print(f"Error: {e} with {features} {traceback_str}")

        df = DataFrame(results)
        if len(df) > 0:
            df = df[df["Test Trade Count"] != 0]
            df = df[df["Train Reward"] > 35]
            df = df[df["Test Precision"] > min_prec_test]

            if len(df) == 0:
                print("No valid results")
                return

            unique_indexes = set(index for sublist in df["Test Indexes"] for index in sublist)
            print(df[["Train Reward", "Train Precision", "Test Precision"]].head(10))
            print(f"Indexes {len(unique_indexes)}")
            print(f"Train Reward Mean {df['Train Reward'].mean()}")
            print(f"Test Reward Mean {df['Test Reward'].mean()}")
            print(f"Test Reward Median {df['Test Reward'].median()}")
            print(f"Test Reward Sum {df['Test Reward'].sum()}")
            print(f"Test Precision {df['Test Precision'].mean()}")
            print(f"Test Trade Count {df['Test Trade Count'].mean()}")

            for i, r in df.iterrows():
                self._save_predictor(symbol=symbol, atr_factor_stop=atr_factor_stop,
                                     atr_factor_limit=atr_factor_limit,
                                     features=list(r["Features"]), trade_mode=trade_mode,
                                     trading_hours=trading_hours,
                                     test_reward=r["Test Reward"],
                                     test_precision=r["Test Precision"],
                                     test_trade_count=r["Test Trade Count"],
                                     unique_indexes=len(unique_indexes),
                                     train_reward=r["Train Reward"],
                                     train_precision=r["Train Precision"],
                                     train_trade_count=r['Test Trade Count'])

        return df

    def _get_random_forest_params(self) -> dict:
        return {
            'n_estimators': [50, 100, 200, 500],  # Anzahl der Bäume
            'max_depth': [3, 5, 7, 10, None],  # Maximale Tiefe der Bäume
            'min_samples_split': [2, 5, 10, 20],  # Mindestanzahl von Samples für Split
            'min_samples_leaf': [1, 2, 4, 10],  # Mindestanzahl von Samples in einem Blatt
            'max_features': ['sqrt', 'log2', None],  # Anzahl der betrachteten Features pro Split
            'criterion': ['gini', 'entropy'],  # Kriterium zur Bestimmung der Qualität eines Splits
            'class_weight': ['balanced', 'balanced_subsample', None]  # Gewichtung für unbalancierte Klassen
        }

    def _train_combo(self, df, features, n_iter):
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning)
        warnings.filterwarnings("ignore", category=RuntimeWarning)
        warnings.filterwarnings("ignore", category=UndefinedMetricWarning, module="sklearn.metrics._classification")

        model_rf = RandomForestClassifier(random_state=42)
        search_rf = RandomizedSearchCV(model_rf,
                                       param_distributions=self._get_random_forest_params(),
                                       n_iter=n_iter,
                                       scoring='precision', cv=3, n_jobs=5)
        X_train = df[list(features)]
        y_train = df[self._target]
        logging.getLogger("sklearn").setLevel(logging.ERROR)
        # Warnungen global unterdrücken
        warnings.simplefilter("ignore", UndefinedMetricWarning)
        # Environment-Variable setzen, damit subprocesses sie erben
        os.environ["PYTHONWARNINGS"] = "ignore"
        search_rf.fit(X_train, y_train)
        best_model_candidate = search_rf.best_estimator_
        return best_model_candidate

    def _get_combos(self, num_features, train_df):
        feature_cols = [col for col in train_df.columns if col != self._target]
        combos = list(combinations(feature_cols, num_features))
        random.shuffle(combos)

        # Kürze die Liste auf 20 % der ursprünglichen Länge
        reduced_size = max(1, int(len(combos) * 0.2))  # Mindestens 1 Element behalten
        return combos[:reduced_size]

    @staticmethod
    def _get_combos_by_best_features(num_features, best_features: List, size=0.6):
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

    def _prepare_df(self, df: DataFrame, symbol: str, trading_hours: int, atr_factor: float) -> DataFrame:
        path = f"{symbol}_{atr_factor}_{trading_hours}"
        y = df[self._target]

        if not self._cache.best_features_exist(path):
            # Initialisiere das Modell
            model = RandomForestClassifier()

            # Features und Zielvariable extrahieren
            x = df.drop(columns=[self._target])

            # Features bereinigen
            cleaned_df = self._filter_features_by_vif_and_precision(x, y, model)
            df = df[cleaned_df.columns]
            df[self._target] = y

            # Auswahl der besten Features pro Kategorie # Berechnung der Feature Importance mit RandomForest
            importance_df = self.feature_importance_xgboost(df, self._target)
            best_features = importance_df.nlargest(30, columns=["Importance"])["Feature"].to_list()
            self._cache.save_best_features(best_features, path)
        else:
            best_features = self._cache.load_best_features(path)
        df = df[best_features]

        df[self._target] = y
        return df

    def train(self, df, trading_hours: int,
              num_features: int,
              trading_mode: str, symbol: str,
              min_prec_train: float, min_prec_test: float, atr_factor_stop: float,
              atr_factor_limit: float,
              best_features: List[str],
              part:float, existing_combos: List = None):

        # if len(best_features) == 0:
        #     df = self._prepare_df(df, symbol, trading_hours, atr_factor)

        self._best_feature_pair_by_reward(df=df,
                                          symbol=symbol,
                                          num_features=num_features,
                                          min_prec_train=min_prec_train, trade_mode=trading_mode,
                                          trading_hours=trading_hours, atr_factor_stop=atr_factor_stop,
                                          atr_factor_limit=atr_factor_limit,
                                          best_features=best_features, min_prec_test=min_prec_test, part=part, existing_combos=existing_combos)

    def create_data(self, tiingo, symbol, trade_type, data_processor, simulation, hours, factor_stop, factor_limit, indicators,
                    trade_mode: str,
                    cache) -> (DataFrame, DataFrame, str):
        df_train, eval_df_train = self._get_train_data(tiingo, symbol, trade_type, data_processor=data_processor,
                                                       dropbox_cache=cache)
        if len(df_train) < 5000:
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
        hour_df = f"{symbol}_train_1hour_5.csv"
        minute_df = f"{symbol}_train_5minute_5.csv"

        if dropbox_cache.train_cache_exist(hour_df) and dropbox_cache.train_cache_exist(minute_df):
            df_train = dropbox_cache.load_train_cache(hour_df)
            eval_df_train = dropbox_cache.load_train_cache(minute_df)
        else:
            df_train, eval_df_train = tiingo.load_test_data(symbol, data_processor, trade_type=trade_type,
                                                            use_cache=True)
            dropbox_cache.save_train_cache(df_train, hour_df)
            dropbox_cache.save_train_cache(eval_df_train, minute_df)

        df_train = df_train.astype({col: 'float32' for col in df_train.select_dtypes(include='float64').columns})
        eval_df_train = eval_df_train.astype(
            {col: 'float32' for col in eval_df_train.select_dtypes(include='float64').columns})
        return df_train, eval_df_train
