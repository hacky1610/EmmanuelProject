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

from Predictors.deep_predictor import DeepPredictor

log_filename = f"best_feature_search_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

# logging.basicConfig(
#     filename=log_filename,  # Log-Datei mit Zeitstempel
#     filemode="a",  # Anhängen, nicht überschreiben
#     level=logging.INFO,  # Nur INFO & ERROR-Level speichern
#     format="%(asctime)s - %(levelname)s - %(message)s",
#     datefmt="%Y-%m-%d %H:%M:%S"
# )

class CombinationTrainer:

    def __init__(self, cache, indicators, predictor_store , test_mode):
        self._cache = cache
        self._indicators = indicators
        self._predictor_store = predictor_store
        self._target = "result"
        self._test_mode =test_mode


    def _filter_features_by_vif_and_precision(self, df, y, model, vif_threshold=5.0, cv_folds=5):
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

    def _predict(self, df:DataFrame, features:List[str], model:object, threshold:float) -> (float, int):

        X_test = df[list(features)]
        y_test = df[self._target]

        y_prob_test = model.predict_proba(X_test)[:, 1]
        y_pred_test = (y_prob_test >= threshold).astype(int)

        test_precision = precision_score(y_test, y_pred_test, zero_division=0)
        test_true_positives = ((y_pred_test == 1) & (y_test == 1)).sum()
        test_false_positives = ((y_pred_test == 1) & (y_test == 0)).sum()
        test_reward = test_true_positives - test_false_positives

        return test_precision, test_reward

    def _predict_dynamic_threshold(self, df: DataFrame, features: List[str], model: object) -> (
    float, int, float):

        X_train = df[list(features)]
        y_train = df[self._target]
        # Wahrscheinlichkeiten statt harte Vorhersagen
        y_prob_train = model.predict_proba(X_train)[:, 1]

        # Optimale Threshold-Suche
        best_local_threshold = 0.5
        best_local_precision = 0.0

        for threshold in [0.45, 0.5, 0.55, 0.6]:
            y_pred_train = (y_prob_train >= threshold).astype(int)
            precision = precision_score(y_train, y_pred_train, zero_division=0)

            if precision > best_local_precision:
                best_local_precision = precision
                best_local_threshold = threshold

        # Mit optimalem Threshold die finale Reward-Berechnung
        y_pred_train = (y_prob_train >= best_local_threshold).astype(int)
        true_positives = ((y_pred_train == 1) & (y_train == 1)).sum()
        false_positives = ((y_pred_train == 1) & (y_train == 0)).sum()
        reward = true_positives - false_positives

        return best_local_precision, reward, best_local_threshold

    def _get_random_forest_params(self) -> dict:
        return  {
                'n_estimators': [50, 100, 200, 500],  # Anzahl der Bäume
                'max_depth': [3, 5, 7, 10, None],  # Maximale Tiefe der Bäume
                'min_samples_split': [2, 5, 10, 20],  # Mindestanzahl von Samples für Split
                'min_samples_leaf': [1, 2, 4, 10],  # Mindestanzahl von Samples in einem Blatt
                'max_features': ['sqrt', 'log2', None],  # Anzahl der betrachteten Features pro Split
                #'bootstrap': [True, False],  # Ob Bootstrapping verwendet wird
                'criterion': ['gini', 'entropy'],  # Kriterium zur Bestimmung der Qualität eines Splits
                'class_weight': ['balanced', 'balanced_subsample', None]  # Gewichtung für unbalancierte Klassen
        }

    def _save_predictor(self,symbol:str, trade_mode:str, trading_hours:int,best_threshold:float, features:List, atr_factor:float, model):
        if self._test_mode:
            return
        ##Save
        dp = DeepPredictor(symbol=symbol, cache=self._cache,
                           indicators=self._indicators, config={})
        dp.set_model_params(trade_mode=trade_mode, trading_hours=trading_hours,
                            threshold=best_threshold, features=list(features),
                            atr_factor=atr_factor)
        dp.set_model(model)
        self._predictor_store.save(dp)

    def  _best_feature_pair_by_reward(self, df:DataFrame, symbol:str,
                                      trading_hours:int, trade_mode:str,
                                      num_features:int,  atr_factor:float, min_prec:float,
                                      n_iter=5):

        if self._test_mode:
            train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)
        else:
            train_df = df

        results = []
        combos = self._get_combos(num_features, train_df)
        total = len(combos)
        last_shown = -1
        for i, features in enumerate(combos):
            try:
                percent = int((i / total) * 100)  # Berechne das Prozent als Ganzzahl
                if percent != last_shown:  # Nur ausgeben, wenn sich der Prozentwert ändert
                    last_shown = percent
                    print(f"Progress: {percent}%")

                best_model_candidate = self._train_combo(df, features, n_iter)

                train_precision, train_reward, best_threshold = self._predict_dynamic_threshold(train_df,  features, best_model_candidate)
                if self._test_mode:
                    test_precision, test_reward = self._predict(test_df,features, best_model_candidate, best_threshold)
                else:
                    test_precision, test_reward = 0,0

                # Mindestbedingungen prüfen
                if train_precision >= min_prec:
                    result = {
                        "Features": features,
                        "Best Model": best_model_candidate,
                        "Best Model Name": best_model_candidate.__class__.__name__,
                        "Train Precision": train_precision,
                        "Train Reward": train_reward,
                        "Test Precision": test_precision,
                        "Test Reward": test_reward,
                        "Best Threshold": best_threshold
                    }
                    results.append(result)
                    result_df = pandas.DataFrame(results)
                    mean = result_df["Test Reward"].mean()
                    sum = result_df["Test Reward"].sum()
                    print(f"{symbol} Best Threshold: {best_threshold:.2f}, Precision: {train_precision:.4f}, Reward: {train_reward} Test Prec {test_precision} Test reward {test_reward} Test Mean {mean} Test Sum {sum} Features: {features} {best_model_candidate.__class__.__name__}")

                    self._save_predictor(symbol=symbol, atr_factor=atr_factor,
                                         features=features,trade_mode=trade_mode,
                                         trading_hours=trading_hours,model=best_model_candidate, best_threshold=best_threshold)
            except Exception as e:
                traceback_str = traceback.format_exc()
                print(f"Error: {e} with {features} {traceback_str}")

        df_results = pd.DataFrame(results)
        df_results.to_csv(f"output_csv{num_features}.csv", index=False)

        return {

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

    def feature_importance_xgboost(self, df, target):
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

    def _prepare_df(self, df:DataFrame, symbol:str, trading_hours:int, atr_factor:float) -> DataFrame:
        path = f"{symbol}_{atr_factor}_{trading_hours}"
        y = df[self._target]

        if not self._cache.best_features_exist(path):
            # Initialisiere das Modell
            model = RandomForestClassifier()

            # Features und Zielvariable extrahieren
            X = df.drop(columns=[self._target])

            # Features bereinigen
            cleaned_df = self._filter_features_by_vif_and_precision(X, y, model)
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

    def train(self, df, trading_hours:int,  num_features:int,
              trading_mode:str, symbol:str,
              min_prec:float, atr_factor:float):

        best_combination = self._best_feature_pair_by_reward(df=self._prepare_df(df,symbol, trading_hours, atr_factor),
                                                             symbol=symbol
                                                             ,num_features=num_features ,
                                                             min_prec=min_prec, trade_mode=trading_mode,
                                                             trading_hours=trading_hours, atr_factor=atr_factor)
        print(best_combination)
        return