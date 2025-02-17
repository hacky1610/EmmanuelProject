# region import

import warnings
from typing import List
from catboost import CatBoostClassifier
import lightgbm as lgb
from imblearn.over_sampling import SMOTE
from keras import Sequential, Input, Model
from keras.src.callbacks import ReduceLROnPlateau, EarlyStopping
from keras.src.layers import Dense, Dropout, BatchNormalization, Add, Reshape, Conv1D, MaxPooling1D, Flatten
from keras.src.optimizers import Adam, SGD, RMSprop, AdamW
from keras.src.optimizers.schedules import ExponentialDecay
from sklearn.decomposition import PCA
import tensorflow as tf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression
from statsmodels.stats.outliers_influence import variance_inflation_factor
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.datasets import load_iris

from sklearn.feature_selection import VarianceThreshold, SelectKBest, f_classif, SelectFromModel, RFE
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, TimeSeriesSplit, GridSearchCV
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, recall_score, f1_score, confusion_matrix
from sklearn.metrics import make_scorer, precision_score
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier, VotingClassifier, GradientBoostingClassifier
import pandas as pd
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, PolynomialFeatures, MinMaxScaler
from xgboost import XGBClassifier

from BL import measure_time
import logging

from BL.combination_trainer import CombinationTrainer

# endregion


class DeepTrainer:

    # Benutzerdefinierte Bewertungsfunktion für `1`-Vorhersagen
    def trade_precision(self, y_true, y_pred):
        # Filter nur für die Trades (y_pred == 1)
        y_pred_filtered = y_pred[y_pred == 1]
        y_true_filtered = y_true[y_pred == 1]

        # Falls keine Trades vorhergesagt wurden
        if len(y_pred_filtered) == 0:
            return 0

        # Berechnung der Präzision für Trades
        return precision_score(y_true_filtered, y_pred_filtered)

    # Scorer für die Cross-Validation

    def get_pipeline_variants(self,model):
        return [
            Pipeline([
                # Small threshold to remove low variance features
                ('classifier', model)
            ])
        ]

    def _get_models(self):
        models =  {

            'CatBoost Regularized': (
                CatBoostClassifier(random_seed=42, verbose=0, loss_function='Logloss'), {
                    'classifier__depth': [4, 6, 8],  # Maximale Baumtiefe
                    'classifier__learning_rate': [0.01, 0.05],  # Lernrate
                    'classifier__iterations': [50, 100],  # Anzahl der Bäume
                    'classifier__l2_leaf_reg': [1, 3, 5, 10],  # L2-Regularisierung (entspricht reg_lambda)
                    'classifier__bagging_temperature': [0, 1, 2],  # Stochastic Gradient Boosting
                    'classifier__border_count': [32, 64, 128],  # Anzahl der Binning-Grenzen für numerische Features
                    'classifier__scale_pos_weight': [0.5, 1.0]  # Ausgleich für unbalancierte Klassen
                }),

            'XGBoost Regularized 2': (
                XGBClassifier(random_state=42, use_label_encoder=False, eval_metric='aucpr', verbosity=0),
                {
                    'classifier__max_depth': [2, 3, 4],
                    'classifier__learning_rate': [0.001, 0.01, 0.05],
                    'classifier__n_estimators': [50, 100, 200],
                    'classifier__gamma': [0.1, 0.5, 1.0],
                    'classifier__subsample': [0.5, 0.8],  # Weniger Overfitting
                    'classifier__colsample_bytree': [0.5, 0.8],  # Weniger Overfitting
                    'classifier__min_child_weight': [10, 20],  # Stärkere Leaf-Constraints
                    'classifier__reg_alpha': [1, 5, 10],  # L1-Regularisierung
                    'classifier__reg_lambda': [5, 10, 20],  # L2-Regularisierung
                    'classifier__scale_pos_weight': [0.5, 1.0, 1.5]
                }),

            'XGBoost Regularized 3': (
                XGBClassifier(random_state=42, use_label_encoder=False, eval_metric='aucpr', verbosity=0), {
                    'classifier__max_depth': [3, 4, 6, 8],
                    'classifier__learning_rate': [0.001, 0.005, 0.01, 0.05],
                    'classifier__n_estimators': [50, 100, 200],
                    'classifier__gamma': [0, 0.1, 0.5, 1.0],
                    'classifier__subsample': [0.6, 0.7, 0.8, 0.9],
                    'classifier__colsample_bytree': [0.6, 0.7, 0.8, 0.9],
                    'classifier__min_child_weight': [1, 5, 10, 20],
                    'classifier__reg_alpha': [0, 0.1, 0.5, 1.0, 2.0],  # L1-Regularisierung
                    'classifier__reg_lambda': [0.1, 1, 5, 10],  # L2-Regularisierung
                    'classifier__scale_pos_weight': [0.5, 1.0, 2.0, 5.0]  # Falls Klassen unausgeglichen sind
                }),

            'XGBoost Regularized 4': (
                XGBClassifier(random_state=42, use_label_encoder=False, eval_metric='aucpr', verbosity=0), {
                    'classifier__max_depth': [2, 3, 4],
                    'classifier__learning_rate': [0.01, 0.05],
                    'classifier__n_estimators': [50, 100],
                    'classifier__gamma': [0.5, 1.0],
                    'classifier__subsample': [0.8],
                    'classifier__colsample_bytree': [0.8],
                    'classifier__min_child_weight': [30, 40],
                    'classifier__reg_alpha': [0.01, 0.1],  # L1-Regularisierung
                    'classifier__reg_lambda': [0.01,0.2],  # L2-Regularisierung
                    'classifier__scale_pos_weight': [0.5, 1.0]
                }),

        }

        return models

    def create_voting_classifier(self, models):

        # Erstelle eine Liste von Modellen für den VotingClassifier
        voting_models = []
        for name, (model, params) in models.items():
            voting_models.append((name, model))

        # Erstelle den VotingClassifier
        voting_clf = VotingClassifier(estimators=voting_models, voting="soft")  # Verwende 'soft' für probabilistische Vorhersagen

        return voting_clf

    # Funktion, die ein Keras-Modell erstellt
    def create_model(self, dropout_rate=0.2, activation='relu', optimizer="adam", size=85):
        model = Sequential()
        # Specify the input shape explicitly with an Input layer
        model.add(Input(shape=(size,)))  # Replace `input_dim` with `Input`
        model.add(Dense(256, activation=activation))
        model.add(Dropout(dropout_rate))
        model.add(Dense(128, activation=activation))
        model.add(Dropout(dropout_rate))
        model.add(Dense(64, activation=activation))
        model.add(Dropout(dropout_rate))
        model.add(Dense(1, activation='sigmoid'))  # Binary classification
        model.compile(optimizer=optimizer, loss='binary_crossentropy', metrics=['accuracy'])
        return model


    def custom_scoring(self,y_true, y_pred):
        """
         Custom scoring function to penalize false positives (1 predicted when y_true is 0)
         and control the percentage of positive predictions.

         Parameters:
         y_true (array-like): True labels (binary, 0 or 1).
         y_pred (array-like): Predicted labels (binary, 0 or 1).
         target_positive_rate (float): Desired proportion of positive predictions (default is 0.1).

         Returns:
         float: Adjusted precision score considering false positives and positive prediction rate.
         """
        # Flatten y_pred if it's a 2D array
        y_pred = y_pred.ravel() if len(y_pred.shape) > 1 else y_pred

        # Convert y_true to NumPy array if it's a Pandas Series
        if isinstance(y_true, pd.Series):
            y_true = y_true.to_numpy()

        # Calculate True Positives (TP) and False Positives (FP)
        true_positives = ((y_pred == 1) & (y_true == 1)).sum()
        false_positives = ((y_pred == 1) & (y_true == 0)).sum()

        # Handle case where no positives are predicted to avoid division by zero
        if true_positives + false_positives == 0:
            return 0.0

        # Calculate precision
        precision = true_positives / (true_positives + false_positives)

        f = 0
        if (y_pred == 1).sum() < (y_true == 1).sum():
            f = (y_pred == 1).sum() / (y_true == 1).sum()

        # Return the precision adjusted by the penalty
        return precision - (1 - f) * 0.2

    @measure_time
    def _train_model(self,pipeline_index,model_name, pipeline, param_grid, tscv,
                     X_train, y_train, X_test, y_test, good_featurs, quantile, hours, iterations, evaluate_type, manual_precision=0):
        print(f"\nTesting pipeline variant {pipeline_index + 1} for {model_name}")
        scorers = {
            'precision': make_scorer(precision_score, pos_label=1, zero_division=0, average='weighted'),
            'recall': make_scorer(recall_score, pos_label=1, zero_division=0),
            'f1_weighted': make_scorer(f1_score, pos_label=1, zero_division=0, average='weighted'),
            'f1_macro': make_scorer(f1_score, pos_label=1, zero_division=0, average='macro')
        }
        random_search = RandomizedSearchCV(
            estimator=pipeline,
            param_distributions=param_grid,
            n_iter=iterations,
            cv=tscv,
            verbose=0,
            n_jobs=3,
            scoring=make_scorer(precision_score, pos_label=1, zero_division=0, average='weighted'),
            random_state=42
        )

        # Führe RandomizedSearch durch und speichere das beste Modell
        random_search.fit(X_train, y_train)

        best_cv_score = random_search.best_score_
        best_model = random_search.best_estimator_

        train_result = self.evaluate_model(best_model, X_train, y_train,
                                      thresholds=[0.45,0.5, 0.55], evaluate_type=evaluate_type)
        test_result = self.evaluate_model(best_model, X_test, y_test,
                                     thresholds=[0.45,0.5, 0.55], evaluate_type=evaluate_type)

        return random_search.best_params_ | {
            "Model": model_name,
            "Pipeline Variant": pipeline_index + 1,
            "Pipeline Name": f"{pipeline}",
            "CV Score": best_cv_score,
            "Trading Houres": hours,
            "Evaluate Type": evaluate_type,
            "Score": (train_result["Best Precision"] + best_cv_score) / 2,
            "Best Reward": test_result["Best Reward"],
            "Best Precision": test_result["Best Precision"],
            "Best Recall": test_result["Best Recall"],
            "Best F1-Score": test_result["Best F1-Score"],
            "Best Threshold": test_result["Best Threshold"],
            "Positive Predictions Count": test_result["Positive Predictions Count"],
            "Best Train Reward": train_result["Best Reward"],
            "Best Train Precision": train_result["Best Precision"],
            "Best Train Recall": train_result["Best Recall"],
            "Best Train F1-Score": train_result["Best F1-Score"],
            "Best Train Threshold": train_result["Best Threshold"],
            "Positive Predictions Count Train": train_result["Positive Predictions Count"],
            "Best Model": best_model,
            "Good Features": good_featurs,
            "Quantile": quantile,
            "Iterations": iterations,
            "Manual Precision": manual_precision,
        }



    def train(self, df_train, df_test, hours, quantile, iterations, evaluate_type, combination_size=3,use_importance=False):
        # Suppress warnings
        warnings.filterwarnings("ignore")


        return []


    @staticmethod
    def analyze_cv_scores(cv_scores, threshold=0.7, warning_threshold=0.05):
        """
        Analysiert die Cross-Validation-Scores und gibt eine Warnung aus, wenn ein Score unter dem Schwellenwert liegt
        oder die Standardabweichung der Scores zu hoch ist.

        :param cv_scores: Liste oder Array der Cross-Validation-Scores.
        :param threshold: Der minimale akzeptable Score (default: 0.7).
        :param warning_threshold: Der Schwellenwert für die Standardabweichung der Scores, um eine Warnung zu generieren (default: 0.05).
        :return: None, gibt eine Warnung aus, wenn erforderlich.
        """

        # Berechne den Mittelwert und die Standardabweichung der Scores
        mean_score = np.mean(cv_scores)
        std_dev = np.std(cv_scores)

        print(f"Durchschnittlicher Cross-Validation Score: {mean_score:.4f}")
        print(f"Standardabweichung der Scores: {std_dev:.4f}")

        # Überprüfe, ob ein Score unter dem festgelegten Schwellenwert liegt
        low_scores = cv_scores[cv_scores < threshold]
        if len(low_scores) > 0:
            print(f"Warnung: Es gibt {len(low_scores)} Score(s) unter dem Schwellenwert von {threshold}.")
            print(f"Betroffene Scores: {low_scores}")

        # Überprüfe, ob die Standardabweichung zu hoch ist
        if std_dev > warning_threshold:
            print(
                f"Warnung: Die Standardabweichung der Scores ist hoch ({std_dev:.4f}). Dies könnte auf eine instabile Modellleistung hinweisen.")

        # Wenn ein Score oder eine Standardabweichung außerhalb der akzeptablen Grenzen liegt, gibt es eine Warnung
        if len(low_scores) > 0 or std_dev > warning_threshold:
            print("ACHTUNG: Das Modell zeigt möglicherweise inkonsistente oder schlechte Leistung!")

    @staticmethod
    # Methode zur konservativen Vorhersage (keine 1 vorhersagen, wenn y=0 ist)
    def conservative_predict(model, X, threshold=0.9):
        probabilities = model.predict_proba(X)[:, 1]
        return (probabilities >= threshold).astype(int)

    @staticmethod
    # Angepasste Validierungsfunktion, die Präzision bei 1 misst
    def evaluate_model(model, X, y, thresholds=None, min_positive_predictions=10, evaluate_type: str = "f1"):
        """
        Bewertet ein Modell basierend auf Precision, Recall und F1-Score.
        - Falls das Modell `predict_proba` unterstützt, wird eine Schwellenwertanalyse durchgeführt.
        - Andernfalls wird nur `predict` verwendet.

        Args:
            model: Das zu bewertende Modell.
            X: Eingabedaten.
            y: Zielvariablen (binär: 0 oder 1).
            thresholds: Liste von Schwellenwerten für die Schwellenwertanalyse (nur bei `predict_proba`).
            min_positive_predictions: Minimale Anzahl an positiven Vorhersagen, um Metriken zu berechnen.

        Returns:
            Dictionary mit den besten Metriken und weiteren Informationen.
        """
        # Überprüfen, ob Schwellenwerte angegeben wurden
        if thresholds is None:
            thresholds = [0.5]  # Standard-Schwellenwert für binäre Klassifikationen

        # Initialisiere Ergebnisse
        results = {
            "Best Precision": 0.0,
            "Best Recall": 0.0,
            "Best F1-Score": 0.0,
            "Best Reward": 0.0,
            "Best Threshold": 0.5,
            "Positive Predictions Count": 0,
            "Details": []  # Detaillierte Ergebnisse für jeden Schwellenwert
        }

        if hasattr(model, "predict_proba"):
            # Das Modell unterstützt `predict_proba`
            y_proba = model.predict_proba(X)[:, 1]

            for threshold in thresholds:
                y_pred_thresholded = (y_proba >= threshold).astype(int)
                positive_predictions = y_pred_thresholded.sum()

                true_positives = ((y_pred_thresholded == 1) & (y == 1)).sum()
                false_positives = ((y_pred_thresholded == 1) & (y == 0)).sum()
                tp_minus_fp = true_positives - false_positives

                # Überprüfe, ob die Anzahl positiver Vorhersagen das Minimum erreicht
                if positive_predictions < min_positive_predictions:
                    precision, recall, f1 = 0.0, 0.0, 0.0
                else:
                    precision = precision_score(y, y_pred_thresholded, pos_label=1, zero_division=0)
                    recall = recall_score(y, y_pred_thresholded, pos_label=1, zero_division=0)
                    f1 = f1_score(y, y_pred_thresholded, pos_label=1, zero_division=0)

                # Speichere Ergebnisse für den aktuellen Schwellenwert
                results["Details"].append({
                    "Threshold": threshold,
                    "Precision": precision,
                    "Recall": recall,
                    "Reward": tp_minus_fp,
                    "F1-Score": f1,
                    "Positive Predictions Count": positive_predictions
                })

                if evaluate_type == "f1":
                    # Aktualisiere die besten Metriken basierend auf dem F1-Score
                    if f1 > results["Best F1-Score"]:
                        results["Best F1-Score"] = f1
                        results["Best Precision"] = precision
                        results["Best Recall"] = recall
                        results["Best Reward"] = tp_minus_fp
                        results["Best Threshold"] = threshold
                        results["Positive Predictions Count"] = positive_predictions
                else:
                    # Aktualisiere die besten Metriken basierend auf dem F1-Score
                    if precision > results["Best Precision"]:
                        results["Best F1-Score"] = f1
                        results["Best Precision"] = precision
                        results["Best Recall"] = recall
                        results["Best Reward"] = tp_minus_fp
                        results["Best Threshold"] = threshold
                        results["Positive Predictions Count"] = positive_predictions

        elif hasattr(model, "predict"):
            # Das Modell unterstützt nur `predict`
            y_pred = model.predict(X)
            positive_predictions = (y_pred == 1).sum()
            true_positives = ((y_pred == 1) & (y == 1)).sum()
            false_positives = ((y_pred == 1) & (y == 0)).sum()
            tp_minus_fp = true_positives - false_positives

            if positive_predictions < min_positive_predictions:
                precision, recall, f1 = 0.0, 0.0, 0.0
            else:
                precision = precision_score(y, y_pred, pos_label=1, zero_division=0)
                recall = recall_score(y, y_pred, pos_label=1, zero_division=0)
                f1 = f1_score(y, y_pred, pos_label=1, zero_division=0)

            # Aktualisiere Ergebnisse
            results["Best Precision"] = precision
            results["Best Recall"] = recall
            results["Best Reward"] = tp_minus_fp
            results["Best F1-Score"] = f1
            results["Positive Predictions Count"] = positive_predictions
            results["Details"].append({
                "Threshold": None,
                "Precision": precision,
                "Recall": recall,
                "Reward": tp_minus_fp,
                "F1-Score": f1,
                "Positive Predictions Count": positive_predictions
            })

        else:
            raise AttributeError("Das Modell muss entweder `predict_proba` oder `predict` unterstützen.")

        return results

    def reduce_multicollinearity(self,features_df, vif_threshold=10):
        from statsmodels.stats.outliers_influence import variance_inflation_factor
        import numpy as np

        X = features_df.drop(columns=['Score']).copy()

        # Ungültige Werte behandeln
        X = X.fillna(0)
        X = X.replace([np.inf, -np.inf], np.nan).dropna(axis=1)

        while True:
            vif_data = pd.DataFrame()
            vif_data["Feature"] = X.columns
            vif_data["VIF"] = [variance_inflation_factor(X.values, i) for i in range(X.shape[1])]

            max_vif = vif_data["VIF"].max()
            if max_vif <= vif_threshold:
                break

            # Feature mit dem höchsten VIF und niedrigstem Score entfernen
            max_vif_feature = vif_data.loc[vif_data["VIF"].idxmax(), "Feature"]
            features_df = features_df[features_df["Feature"] != max_vif_feature]
            X = features_df.drop(columns=['Score'])

        return features_df






