# region import
import math
import os
import sys
from itertools import combinations

from statsmodels.stats.outliers_influence import variance_inflation_factor
from sklearn.preprocessing import MinMaxScaler
import pandas as pd
import warnings
from typing import List
import numpy as np
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
from sklearn.model_selection import train_test_split
from sklearn.datasets import load_iris

from sklearn.feature_selection import VarianceThreshold, SelectKBest, f_classif, SelectFromModel, RFE
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, TimeSeriesSplit, GridSearchCV
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, recall_score, f1_score
from sklearn.metrics import make_scorer, precision_score
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier, VotingClassifier, GradientBoostingClassifier
import pandas as pd
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, PolynomialFeatures, MinMaxScaler
from xgboost import XGBClassifier

from BL import measure_time

class SilentCallback(tf.keras.callbacks.Callback):
    def on_epoch_end(self, epoch, logs=None):
        pass

# endregion
class KerasWrapper(BaseEstimator, ClassifierMixin):
    def __init__(self, dropout_rate=0.2, optimizer='adam',
                 learning_rate=0.001, epochs=50, batch_size=32,
                 model_type="V1", activation='relu',regularizer=None, initializer="he_normal"):
        self.dropout_rate = dropout_rate
        self.optimizer = optimizer
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.batch_size = batch_size
        self.model_ = None  # Placeholder for the model
        self.model_type = model_type
        self.activation = activation
        self.regularizer = regularizer
        self.initializer = initializer

    def _build_model(self, input_dim):
        print(f"Building model with type {self.model_type}")
        if self.model_type == "V1":
            model = Sequential([
                Input(shape=(input_dim,)),  # Explicitly define the input shape here
                Dense(64, activation=self.activation),
                Dropout(self.dropout_rate),
                Dense(32, activation=self.activation),
                Dropout(self.dropout_rate),
                Dense(1, activation='sigmoid')  # Binary classification output
            ])
        elif self.model_type == "V2":
            model = Sequential([
                Input(shape=(input_dim,)),
                Dense(128, activation=self.activation),
                BatchNormalization(),
                Dropout(self.dropout_rate),
                Dense(64, activation=self.activation),
                BatchNormalization(),
                Dropout(self.dropout_rate),
                Dense(32, activation=self.activation),
                BatchNormalization(),
                Dropout(self.dropout_rate),
                Dense(1, activation='sigmoid')
            ])
        elif self.model_type == "V3":
            model = Sequential([
                Input(shape=(input_dim,)),
                Dense(128, activation=self.activation, kernel_initializer=self.initializer ),
                Dropout(self.dropout_rate),
                Dense(64, activation=self.activation, kernel_initializer=self.initializer),
                BatchNormalization(),
                Dense(32, activation=self.activation, kernel_initializer=self.initializer),
                Dropout(self.dropout_rate),
                Dense(1, activation='sigmoid')
            ])
        elif self.model_type == "V4":
            input_layer = Input(shape=(input_dim,))
            dense1 = Dense(64, activation=self.activation)(input_layer)
            dropout1 = Dropout(self.dropout_rate)(dense1)
            dense2 = Dense(64, activation=self.activation)(dropout1)
            residual = Add()([dense1, dense2])  # Residual Connection
            dropout2 = Dropout(self.dropout_rate)(residual)
            output_layer = Dense(1, activation='sigmoid')(dropout2)

            model = Model(inputs=input_layer, outputs=output_layer)
        elif self.model_type == "V5":
            model = Sequential([
                Input(shape=(input_dim,)),  # Explizite Eingabeform
                Reshape((input_dim, 1)),  # Keine Angabe von `input_shape`
                Conv1D(filters=32, kernel_size=3, activation=self.activation),
                MaxPooling1D(pool_size=2),
                Flatten(),
                Dense(64, activation=self.activation),
                Dropout(self.dropout_rate),
                Dense(1, activation='sigmoid')
            ])

        optimizer = None
        if self.optimizer == 'adam':
            optimizer = Adam(learning_rate=self.learning_rate)
        elif self.optimizer == 'sgd':
            optimizer = SGD(learning_rate=self.learning_rate)
        elif self.optimizer == 'rmsprop':
            optimizer = RMSprop(learning_rate=self.learning_rate)
        elif self.optimizer == 'adamw':
            optimizer = AdamW(learning_rate=self.learning_rate)

        model.compile(optimizer=optimizer, loss='binary_crossentropy', metrics=['Precision'])
        return model

    def fit(self, X, y):
        import logging

        early_stopping = EarlyStopping(
            monitor='Precision',  # Überwacht den Validierungsverlust
            patience=10,  # Anzahl der Epochen ohne Verbesserung
            restore_best_weights=True  # Beste Gewichte wiederherstellen
        )

        reduce_lr = ReduceLROnPlateau(
            monitor='Precision',  # Überwacht den Validierungsverlust
            factor=0.5,  # Faktor, um den die Lernrate reduziert wird
            patience=5,  # Anzahl der Epochen ohne Verbesserung
            min_lr=1e-6  # Minimal erlaubte Lernrate
        )
        self.model_ = self._build_model(input_dim=X.shape[1])
        self.model_.fit(X, y, epochs=self.epochs, batch_size=self.batch_size, verbose=0,callbacks=[early_stopping, reduce_lr])


        self.classes_ = np.array([0, 1])  # Convert to NumPy array
        return self

    def predict(self, X):
        proba = self.model_.predict(X)
        return (proba > 0.5).astype(int).flatten()

    def predict_proba(self, X):
        proba = self.model_.predict(X)
        return np.hstack([(1 - proba), proba])

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
            ]),
        ]

    def _get_models(self):
        models =  {


            'XGBoost Weighted': (
                XGBClassifier(random_state=42, use_label_encoder=False, eval_metric='logloss', verbosity=0), {
                    'classifier__max_depth': [3, 5, 7],
                    'classifier__learning_rate': [0.01, 0.1, 0.2],
                    'classifier__n_estimators': [100, 200],
                    'classifier__gamma': [0, 0.1, 0.5, 1],
                    'classifier__subsample': [0.8, 1.0],
                    'classifier__colsample_bytree': [0.8, 1.0],
                    'classifier__min_child_weight': [1, 5, 10],  # Minimale Anforderungen an Split
                    'classifier__scale_pos_weight': [0.3, 0.5, 0.7, 1.0]
                    # Teste verschiedene Gewichtungen für Klasse 1
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
        scorer = make_scorer(precision_score, pos_label=1, zero_division=0)
        random_search = RandomizedSearchCV(
            estimator=pipeline,
            param_distributions=param_grid,
            n_iter=iterations,
            cv=tscv,
            verbose=0,
            n_jobs=3,
            scoring=scorer,
            random_state=42
        )

        # Führe RandomizedSearch durch und speichere das beste Modell
        random_search.fit(X_train, y_train)

        best_cv_score = random_search.best_score_
        best_model = random_search.best_estimator_

        train_result = self.evaluate_model(best_model, X_train, y_train,
                                      thresholds=np.arange(0.1, 1.0, 0.05).tolist(), evaluate_type=evaluate_type)
        test_result = self.evaluate_model(best_model, X_test, y_test,
                                     thresholds=[train_result["Best Threshold"]], evaluate_type=evaluate_type)

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



    def train(self, df, hours, quantile, iterations, evaluate_type, combination_size=3):
        # Suppress warnings
        warnings.filterwarnings("ignore")

        df = df.drop(columns=["chart_index"])
        # Split dataset into training and test sets
        df_train = df[:int(len(df) * 0.8)]
        df_test = df[int(len(df) * 0.8):]

        fe = FeatureEngineering()
        res = fe.evaluate_features(df_train, "result", quantile, combination_size=combination_size)
        best_results = []

        rec = res["Evaluation"]
        print(f"Ev {rec}")

        precicion, reward = fe.calculate_precision(df_test,list(res["Top_Features"]))
        print(f"*******************{precicion}")

        selected_features = list(res["Top_Features"])
        print(selected_features)
        res_list = self.train_features(best_results, df_test, df_train, evaluate_type, hours, iterations, quantile,
                                       selected_features, manual_precision=precicion)

        for d in res_list:
            d.update(rec)
            d.update({"manual reward test":reward})


        return res_list


    def train_features(self, best_results, df_test, df_train, evaluate_type, hours, iterations, quantile,
                       selected_features,manual_precision):
        X_train = df_train.drop(columns=['result'])[selected_features]
        X_test = df_test.drop(columns=['result'])[selected_features]
        y_train = df_train['result']
        y_test = df_test['result']
        scaler = MinMaxScaler()
        X_train = scaler.fit_transform(X_train)
        X_test = scaler.transform(X_test)


        # Apply SMOTE only on the training set
        smote = SMOTE(random_state=42)
        X_train, y_train = smote.fit_resample(X_train, y_train)
        # Models and parameter grids
        models = self._get_models()
        # Cross-validation
        tscv = TimeSeriesSplit(n_splits=5)
        for model_name, (model, param_grid) in models.items():
            print(f"Training {model_name}...")

            # Hole die verschiedenen Pipeline-Varianten
            pipeline_variants = self.get_pipeline_variants(model)

            for i, pipeline in enumerate(pipeline_variants):
                res = self._train_model(pipeline_index=i, model_name=model_name, pipeline=pipeline,
                                        param_grid=param_grid, tscv=tscv, X_train=X_train, y_train=y_train,
                                        X_test=X_test, y_test=y_test, good_featurs=selected_features, quantile=quantile,
                                        hours=hours, iterations=iterations, evaluate_type=evaluate_type, manual_precision=manual_precision)

                best_results.append(res)
        # Ausgabe des besten Modells basierend auf Test-Precision
        # best_model_name = max(results, key=lambda k: results[k][0])
        # best_test_precision, best_model = results[best_model_name]
        best_item = max(best_results, key=lambda x: x['Score'])
        print(f"Precision {best_item['Best Precision']} from {best_item['Model']} - {best_item['Pipeline Name']}")
        return best_results

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





import pandas as pd
import numpy as np
from sklearn.feature_selection import RFE, f_classif, chi2, SelectKBest
from sklearn.linear_model import LassoCV, RidgeCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from statsmodels.stats.outliers_influence import variance_inflation_factor

class FeatureEngineering:
    def correlation_with_target(self, df, target):
        return df.corr()[target].drop(target)

    def feature_importance(self, df, target):
        X = df.drop(columns=[target])
        y = df[target]
        model = RandomForestClassifier(random_state=42)
        model.fit(X, y)
        importance = model.feature_importances_
        return pd.DataFrame({'Feature': X.columns, 'Importance': importance}).sort_values(by='Importance', ascending=False)

    def calculate_vif(self, df):
        vif_data = pd.DataFrame()
        vif_data['Variable'] = df.columns
        vif_data['VIF'] = [variance_inflation_factor(df.values, i) for i in range(df.shape[1])]
        return vif_data

    def remove_high_vif_features(self, df, threshold=5.0):
        vif_df = self.calculate_vif(df)
        while vif_df['VIF'].max() > threshold:
            feature_to_remove = vif_df.sort_values('VIF', ascending=False).iloc[0]['Variable']
            df = df.drop(columns=[feature_to_remove])
            vif_df = self.calculate_vif(df)
        return df

    def select_features_with_rfe(self, df, target, n_features):
        X = df.drop(columns=[target])
        y = df[target]
        model = RandomForestClassifier(random_state=42)
        rfe = RFE(model, n_features_to_select=n_features)
        rfe.fit(X, y)
        selected_features = X.columns[rfe.support_]
        return selected_features

    def select_features_with_stat_tests(self, df, target):
        X = df.drop(columns=[target])
        y = df[target]
        if y.nunique() == 2:  # Binary target
            chi2_selector = SelectKBest(chi2, k='all').fit(X, y)
            scores = chi2_selector.scores_
        else:  # Continuous target
            f_selector = SelectKBest(f_classif, k='all').fit(X, y)
            scores = f_selector.scores_
        return pd.DataFrame({'Feature': X.columns, 'Score': scores}).sort_values(by='Score', ascending=False)

    def select_features_with_embedded_methods(self, df, target):
        X = df.drop(columns=[target])
        y = df[target]

        lasso = LassoCV(cv=5, random_state=42).fit(X, y)
        ridge = RidgeCV(cv=5).fit(X, y)

        lasso_coef = pd.Series(lasso.coef_, index=X.columns)
        ridge_coef = pd.Series(ridge.coef_, index=X.columns)

        lasso_selected = lasso_coef[lasso_coef != 0].index
        ridge_selected = ridge_coef[ridge_coef != 0].index

        return list(set(lasso_selected).intersection(ridge_selected))

    def precision_with_target(self, df, target):
        """Berechnet die Precision jedes Features im Vergleich zum Zielwert."""
        y_true = df[target]
        precision_scores = {}
        for feature in df.drop(columns=[target]).columns:
            # Precision direkt berechnen, da Features bereits binär sind
            y_pred = df[feature]
            precision_scores[feature] = precision_score(y_true, y_pred, zero_division=0, average='macro')
        return pd.Series(precision_scores)

    def best_feature_combination(self,df, target, top_features, combination_size=3):
        """
        Findet die beste Kombination von Features basierend auf der Precision.

        Args:
            df (pd.DataFrame): Der DataFrame mit den Features und dem Zielwert.
            target (str): Der Name der Zielspalte.
            top_features (list): Liste der Top-Features, die berücksichtigt werden sollen.
            combination_size (int): Die Anzahl der Features pro Kombination (Standard: 3).

        Returns:
            dict: Die beste Kombination und die zugehörige Precision.
        """
        y_true = df[target]
        best_combination = None
        best_precision = 0
        best_reward = 0
        weeks = len(df) / 24 / 5

        # Iteriere über alle möglichen Kombinationen von Features
        for combination in combinations(top_features, combination_size):
            # Kombinierte Vorhersage: Logisches ODER der Werte der Features
            y_pred = df[list(combination)].all(axis=1).astype(int)
            true_positives = ((y_pred == 1) & (y_true == 1)).sum()
            false_positives = ((y_pred == 1) & (y_true == 0)).sum()
            tp_minus_fp = true_positives - false_positives


            # Berechne die Precision für diese Kombination
            precision = precision_score(y_true, y_pred, zero_division=0)
            trade_weeks = y_pred.sum() / weeks

            if trade_weeks <= 3:
                continue

            # Speichere die beste Kombination
            if tp_minus_fp > best_reward:
                best_precision = precision
                best_combination = combination
                best_reward = tp_minus_fp

        return {
            "Best_Features": best_combination,
            "Best_Precision": best_precision,
            "Best_Reward": best_reward
        }

    @staticmethod
    def calculate_precision(test_df, features_list, target_column='result'):
        """
        Berechnet die Präzision, indem die Werte der Feature-Spalten mit UND verknüpft werden.

        Args:
            test_df (pd.DataFrame): Der Test-DataFrame, der die relevanten Spalten enthält.
            features_list (list): Liste der Feature-Spalten, die verknüpft werden.
            target_column (str): Name der Spalte mit den tatsächlichen Werten (Default: 'result').

        Returns:
            float: Präzisionswert für die Vorhersagen.
        """
        # Sicherstellen, dass die erforderlichen Spalten vorhanden sind
        missing_features = [feature for feature in features_list if feature not in test_df]
        if missing_features:
            raise ValueError(f"Die folgenden Features fehlen im DataFrame: {missing_features}")

        if target_column not in test_df:
            raise ValueError(f"Die Zielspalte '{target_column}' fehlt im DataFrame.")

        weeks = len(test_df) / 24 / 5



        # Vorhersage (y_pred) erstellen, indem die Features mit UND verknüpft werden
        y_pred = test_df[features_list].all(axis=1).astype(int)


        # Zielspalte extrahieren
        y_true = test_df[target_column]
        true_positives = ((y_pred == 1) & (y_true == 1)).sum()
        false_positives = ((y_pred == 1) & (y_true == 0)).sum()

        reward = true_positives - false_positives

        trade_weeks = y_pred.sum() / weeks

        #if trade_weeks <= 2:
        #    return 0

        # Präzision berechnen
        precision = precision_score(y_true, y_pred)
        return precision, reward

    def evaluate_features(self, df, target, quantile=0.75, vif_threshold=5.0, combination_size=3):

        # Step 3: Remove high VIF features
        df_reduced_vif = self.remove_high_vif_features(df.drop(columns=[target]), threshold=vif_threshold)
        df_reduced_vif[target] = df[target]

        # Step 1: Precision with target
        precision = self.precision_with_target(df_reduced_vif, target)

        # Step 2: Feature importance with RandomForest
        importance_df = self.feature_importance(df_reduced_vif, target)

        # Step 4: Feature selection with RFE
        #selected_rfe_features = self.select_features_with_rfe(df_reduced_vif, target, n_features)

        # Step 5: Feature selection with statistical tests
        #stat_test_features = self.select_features_with_stat_tests(df_reduced_vif, target)

        # Step 6: Embedded methods (LASSO and Ridge)
        #embedded_features = self.select_features_with_embedded_methods(df_reduced_vif, target)

        # Combine scores
        combined_scores = pd.DataFrame({
            'Feature': df_reduced_vif.columns,
            'Precision': precision.reindex(df_reduced_vif.columns).fillna(0),
           # 'Importance': importance_df.set_index('Feature')['Importance'].reindex(df_reduced_vif.columns).fillna(0)
        })

        # VIF values
        vif_df = self.calculate_vif(df_reduced_vif.drop(columns=[target]))
        combined_scores['VIF'] = combined_scores['Feature'].map(vif_df.set_index('Variable')['VIF'])

        # Combined score calculation
        scaler = MinMaxScaler()
        combined_scores[['Precision_transformed',  'VIF_transformed']] = scaler.fit_transform(
            combined_scores[['Precision',  'VIF']]
        )

        # Umkehren der VIF-Skalierung (niedrigere VIF-Werte sind besser)
        combined_scores['VIF_transformed'] = 1 - combined_scores['VIF_transformed']

        # Finalen Score berechnen
        combined_scores['Score'] = (
                combined_scores['Precision_transformed']
               # combined_scores['VIF_transformed']
        )

        # Filter top features
        high_score_threshold = combined_scores['Score'].quantile(quantile)
        top_features = combined_scores[combined_scores['Score'] > high_score_threshold]

        # Ensure target is not included
        top_features = top_features[top_features['Feature'] != target]

        res = self.best_feature_combination(df_reduced_vif, target, top_features['Feature'], combination_size=combination_size)

        # Evaluate feature quality
        num_features = len(top_features)
        avg_precision = top_features['Precision'].mean()
        max_precision = top_features['Precision'].max()
        avg_vif = top_features['VIF'].mean()

        evaluation = {
            'num_features_eval': num_features,
            'avg_precision_eval': avg_precision,
            'max_precision_eval': max_precision,
            'best_features_eval': res["Best_Features"],
            'best_precision_eval': res["Best_Precision"],
            'best_reward_eval': res["Best_Reward"],
            'avg_vif': avg_vif,
            'recommend_training': num_features >= 5 and res["Best_Precision"] >= 0.66 and avg_vif < vif_threshold
        }

        return {
            'Top_Features': top_features['Feature'].tolist(),
            'Best_Features': res["Best_Features"],
            'Evaluation': evaluation
        }











