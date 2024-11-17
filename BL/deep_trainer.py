# region import
import warnings
from typing import List
import numpy as np
from catboost import CatBoostClassifier
import lightgbm as lgb
from imblearn.over_sampling import SMOTE
from keras import Sequential, Input
from keras.src.layers import Dense, Dropout
from keras.src.optimizers import Adam
from keras.src.optimizers.schedules import ExponentialDecay
from sklearn.decomposition import PCA
import tensorflow as tf
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


# endregion

class MyKerasClassifier(BaseEstimator, ClassifierMixin):
    def __init__(self, build_fn=None, epochs=10, batch_size=32, verbose=0, optimizer="adam", dropout_rate=0.2, activation="relu"):
        self.build_fn = build_fn
        self.epochs = epochs
        self.batch_size = batch_size
        self.activation = activation
        self.verbose = verbose
        self.optimizer = optimizer
        self.dropout_rate = dropout_rate
        self.model = None


    def fit(self, X, y):
        # Create the model using the build_fn function
        self.classes_ = np.unique(y)
        self.model = self.build_fn(dropout_rate=self.dropout_rate, activation=self.activation, optimizer=self.optimizer, size= X.shape[1] )
        # Fit the model to the training data
        self.model.fit(X, y, epochs=self.epochs, batch_size=self.batch_size, verbose=self.verbose)
        return self

    def predict(self, X):
        # Predict class labels
        return np.argmax(self.model.predict(X), axis=-1)

    def predict_proba(self, X):
        # Predict class probabilities
        return self.model.predict(X)
    def score(self, X, y):
        # Evaluate the model on the test data
        return self.model.evaluate(X, y, verbose=0)[1]  # Return accuracy

class DeepTrainer:

    def train(self, df) -> (RandomForestClassifier, float):
        rf, accuracy = self._train_random_forest(df)

        return rf, accuracy


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
        # Definiere verschiedene Pipelines mit unterschiedlichen Konfigurationen
        gradient_model = GradientBoostingClassifier()
        return [
            # Pipeline([
            #     ('scaler', MinMaxScaler()),  # Variante 3: MinMaxScaler + PCA
            #     ('pca', PCA(n_components=10)),
            #     ('variance_threshold', VarianceThreshold(threshold=0.0)),
            #     ('classifier', model)
            # ]),
            # Pipeline([
            #     ('scaler', MinMaxScaler()),
            #     ('pca', PCA(n_components=5)),  # Keep top 5 components
            #     ('classifier', model)
            # ]),
            # Pipeline([
            #     ('scaler', MinMaxScaler()),
            #     ('pca', PCA(n_components=10)),  # Keep top 10 components
            #     ('classifier', model)
            # ]),
            # Pipeline([
            #     ('scaler', MinMaxScaler()),
            #     ('pca', PCA(n_components=15)),  # Keep top 15 components
            #     ('classifier', model)
            # ]),
            Pipeline([
                ('scaler', MinMaxScaler()),
                ('variance_threshold', VarianceThreshold(threshold=0.01)),
                # Small threshold to remove low variance features
                ('classifier', model)
            ]),
            Pipeline([
                ('scaler', MinMaxScaler()),  # Skaliert die Features auf einen Bereich [0, 1]
                ('variance_threshold', VarianceThreshold(threshold=0.01)),  # Entfernt Features mit geringer Varianz
                ('feature_selection', SelectFromModel(estimator=gradient_model, threshold="median")),
                # Wählt wichtige Features basierend auf Feature-Wichtigkeit
                ('classifier', model)  # Klassifikator
            ]),
            # Pipeline([
            #     ('scaler', MinMaxScaler()),
            #     ('variance_threshold', VarianceThreshold(threshold=0.1)),
            #     # Higher threshold for more aggressive filtering
            #     ('classifier', model)
            # ]),
            Pipeline([
                ('scaler', MinMaxScaler()),
                ('rfe', RFE(estimator=RandomForestClassifier(random_state=42), n_features_to_select=10)),
                # Keep top 10 features
                ('classifier', model)
            ]),
            Pipeline([
                ('scaler', MinMaxScaler()),
                ('feature_selection', SelectKBest(score_func=f_classif, k=30)),
                # Keep top 10 features
                ('classifier', model)
            ]),
            # Pipeline([
            #     ('scaler', MinMaxScaler()),
            #     ('rfe', RFE(estimator=RandomForestClassifier(random_state=42), n_features_to_select=15)),
            #     # Keep top 15 features
            #     ('classifier', model)
            # ])
        ]

    def _get_models(self):
        lr_schedule = ExponentialDecay(
            initial_learning_rate=0.01, decay_steps=100000, decay_rate=0.96, staircase=True
        )
        return {
            # 'Random Forest': (RandomForestClassifier(random_state=42), {
            #     'classifier__n_estimators': [100, 200, 300],
            #     'classifier__max_depth': [10, 20],
            # }),
        #     "keras" : (MyKerasClassifier(build_fn=self.create_model, verbose=0), {
        #          'classifier__optimizer': ['adam', 'rmsprop', "sgd", Adam(learning_rate=0.001), Adam(learning_rate=lr_schedule)],
        #         'classifier__activation': ["tanh", "elu", "swish"],
        #         'classifier__dropout_rate': [0.2, 0.3, 0.4],
        #         'classifier__epochs': [10, 20],  # Reduziere für schnelle Tests
        #         'classifier__batch_size': [32, 64],
        # }),
            'Gradient Boosting': (GradientBoostingClassifier(random_state=42), {
                'classifier__n_estimators': [50, 100, 200],
                'classifier__max_depth': [3, 5, 7],
                'classifier__learning_rate': [0.01, 0.1, 0.2],
            }),
            'Gradient Boosting 2': (GradientBoostingClassifier(random_state=42), {
                'classifier__n_estimators': [50, 100, 200],
                'classifier__max_depth': [3, 5, 7],
                'classifier__learning_rate': [0.01, 0.1, 0.2],
                'classifier__subsample': [0.8, 1.0],
            }),
            'Gradient Boosting 3': (GradientBoostingClassifier(random_state=42), {
                'classifier__n_estimators': [50, 100, 200],
                'classifier__max_depth': [3, 5, 7],
                'classifier__learning_rate': [0.01, 0.1, 0.2],
                'classifier__subsample': [0.8, 1.0],
                'classifier__min_samples_split': [2, 5, 10],
                'classifier__min_samples_leaf': [1, 3, 5],
                'classifier__max_features': ['auto', 'sqrt', 'log2'],
                'classifier__max_leaf_nodes': [None, 10, 20, 30],
                'classifier__warm_start': [True, False],
                'classifier__validation_fraction': [0.1, 0.2],
                'classifier__n_iter_no_change': [None, 5, 10]
            }),
            'Random Forest Balanced': (RandomForestClassifier(random_state=42, class_weight='balanced'), {
                'classifier__n_estimators': [50, 100, 200],
                'classifier__max_depth': [10, 20],
                'classifier__min_samples_split': [2, 5],
                'classifier__min_samples_leaf': [1, 2, 4],
                'classifier__max_features': ['sqrt'],
                'classifier__bootstrap': [True, False],
            }),
            'XGBoost': (XGBClassifier(random_state=42, use_label_encoder=False, eval_metric='logloss',  verbosity=0), {
                   'classifier__max_depth': [3, 5, 7, 10, 12],             # Explore shallower to deeper trees
                    'classifier__learning_rate': [0.01, 0.05, 0.1, 0.2],   # Test smaller learning rates
                    'classifier__n_estimators': [50, 100, 200, 300, 500],   # Cover a wider range of estimators
                    'classifier__subsample': [0.6, 0.8, 1.0],               # Tweak sampling rate to control overfitting
                    'classifier__colsample_bytree': [0.6, 0.8, 1.0]         # Contr
            }),
            'XGBoost Weighted': (
            XGBClassifier(random_state=42, use_label_encoder=False, eval_metric='logloss', verbosity=0), {
                'classifier__max_depth': [3, 5, 7],
                'classifier__learning_rate': [0.01, 0.1, 0.2],
                'classifier__n_estimators': [100, 200],
                'classifier__subsample': [0.8, 1.0],
                'classifier__colsample_bytree': [0.8, 1.0],
                'classifier__scale_pos_weight': [5, 10, 20]  # Teste verschiedene Gewichtungen für Klasse 1
            }),
            'Random Forest Balanced Weighted': (RandomForestClassifier(random_state=42, class_weight={0: 1, 1: 10}), {
                'classifier__n_estimators': [50, 100, 200],
                'classifier__max_depth': [10, 20],
                'classifier__min_samples_split': [2, 5],
                'classifier__min_samples_leaf': [1, 2, 4],
                'classifier__max_features': ['sqrt'],
                'classifier__bootstrap': [True, False],
            }),
            'LightGBM': (lgb.LGBMClassifier(random_state=42, verbose=-1),
                         {
                             'classifier__max_depth': [3, 5, 7, 10, 12],
                             # Ähnlich wie XGBoost, tiefere und flachere Bäume testen
                             'classifier__learning_rate': [0.01, 0.05, 0.1, 0.2],  # Geringere Lernraten ausprobieren
                             'classifier__n_estimators': [50, 100, 200, 300, 500],
                             # Größerer Bereich für die Anzahl der Bäume
                             'classifier__subsample': [0.6, 0.8, 1.0],
                             # Sampling-Rate zum Überanpassungskontrolle anpassen
                             'classifier__colsample_bytree': [0.6, 0.8, 1.0]  # Anteil der Spalten für Baumaufbau
                         }),
            'LightGBM Weighted (is_unbalance)': (
            lgb.LGBMClassifier(random_state=42, is_unbalance=True, verbose=-1),
            {
                'classifier__max_depth': [3, 5, 7],
                'classifier__learning_rate': [0.01, 0.1],
                'classifier__n_estimators': [100, 200],
                'classifier__subsample': [0.8, 1.0],
                'classifier__colsample_bytree': [0.8, 1.0],
            }
        ),
            'LightGBM Weighted (scale_pos_weight)': (
                lgb.LGBMClassifier(random_state=42, verbose=-1),
                {
                    'classifier__max_depth': [3, 5, 7],
                    'classifier__learning_rate': [0.01, 0.1],
                    'classifier__n_estimators': [100, 200],
                    'classifier__subsample': [0.8, 1.0],
                    'classifier__colsample_bytree': [0.8, 1.0],
                    'classifier__scale_pos_weight': [5, 10, 20],  # Experimentiere mit Werten
                }
            ),
            'CatBoost': (CatBoostClassifier(random_seed=42, verbose=0),
                         {
                             'classifier__depth': [3, 5, 7, 10, 12],  # Baumtiefe
                             'classifier__learning_rate': [0.01, 0.05, 0.1, 0.2],  # Lernrate
                             'classifier__iterations': [50, 100, 200, 300, 500],
                             # Anzahl der Iterationen (entspricht n_estimators)
                             'classifier__subsample': [0.6, 0.8, 1.0],  # Sampling-Rate
                             'classifier__colsample_bylevel': [0.6, 0.8, 1.0]  # Anteil der Spalten auf Ebene
                         }),
            'CatBoost Weighted': (CatBoostClassifier(random_seed=42, verbose=0, class_weights=[1, 10]), {
                'classifier__depth': [3, 5, 7],
                'classifier__learning_rate': [0.01, 0.1],
                'classifier__iterations': [100, 200],
                'classifier__subsample': [0.8, 1.0],
            }),
            'CatBoost Weighted 2': (CatBoostClassifier(random_seed=42, verbose=0, class_weights=[10, 1]), {
                'classifier__depth': [3, 5, 7],
                'classifier__learning_rate': [0.01, 0.1],
                'classifier__iterations': [100, 200],
                'classifier__subsample': [0.8, 1.0],
            }),

            'Logistic Regression': (LogisticRegression(random_state=42, max_iter=1000), {
                'classifier__C': [0.1, 1, 10],
                'classifier__penalty': ['l2'],
                'classifier__solver': ['lbfgs', 'saga'],
            }),
            'Logistic Regression Weighted': (
            LogisticRegression(random_state=42, max_iter=1000, class_weight={0: 1, 1: 10}), {
                'classifier__C': [0.1, 1, 10],
                'classifier__penalty': ['l2'],
                'classifier__solver': ['lbfgs', 'saga'],
            }),
            'Logistic Regression Weighted 2': (
                LogisticRegression(random_state=42, max_iter=1000, class_weight={0: 10, 1: 1}), {
                    'classifier__C': [0.1, 1, 10],
                    'classifier__penalty': ['l2'],
                    'classifier__solver': ['lbfgs', 'saga'],
                }),

            'Support Vector Machine': (SVC(probability=True, random_state=42), {
                'classifier__C': [0.1, 1, 10],
                'classifier__kernel': ['linear', 'rbf'],
                'classifier__gamma': ['scale', 'auto'],
            }),
            'Support Vector Machine Weighted': (SVC(probability=True, random_state=42, class_weight={0: 1, 1: 10}), {
                'classifier__C': [0.1, 1, 10],
                'classifier__kernel': ['linear', 'rbf'],
                'classifier__gamma': ['scale', 'auto'],
            }),

            'Support Vector Machine Weighted 2': (SVC(probability=True, random_state=42, class_weight={0: 10, 1: 1}), {
                'classifier__C': [0.1, 1, 10],
                'classifier__kernel': ['linear', 'rbf'],
                'classifier__gamma': ['scale', 'auto'],
            }),
        }

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

        print((y_pred == 1).sum())
        print((y_true == 1).sum())
        f = 0
        if (y_pred == 1).sum() < (y_true == 1).sum():
            f = (y_pred == 1).sum() / (y_true == 1).sum()

        # Return the precision adjusted by the penalty
        return precision - (1 - f) * 0.5

    def _train_random_forest(self, df):
        # Suppress warnings
        warnings.filterwarnings("ignore")

        df = df.drop(columns=["chart_index"])
        # Split dataset into training and test sets
        df_train = df[:int(len(df) * 0.9)]
        df_test = df[int(len(df) * 0.9):]
        X_train, y_train = df_train.drop(columns=['result']), df_train['result']
        X_test, y_test = df_test.drop(columns=['result']), df_test['result']

        # Apply SMOTE only on the training set
        smote = SMOTE(random_state=42)
        X_train, y_train = smote.fit_resample(X_train, y_train)

        # Models and parameter grids
        models = self._get_models()

        # Cross-validation
        tscv = TimeSeriesSplit(n_splits=5)

        def evaluate_model(model, X, y, thresholds=None, min_positive_predictions=10):
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
                "Best Threshold": None,
                "Positive Predictions Count": 0,
                "Details": []  # Detaillierte Ergebnisse für jeden Schwellenwert
            }

            if hasattr(model, "predict_proba"):
                # Das Modell unterstützt `predict_proba`
                y_proba = model.predict_proba(X)[:, 1]

                for threshold in thresholds:
                    y_pred_thresholded = (y_proba >= threshold).astype(int)
                    positive_predictions = y_pred_thresholded.sum()

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
                        "F1-Score": f1,
                        "Positive Predictions Count": positive_predictions
                    })

                    # Aktualisiere die besten Metriken basierend auf dem F1-Score
                    if precision > results["Best Precision"]:
                        results["Best F1-Score"] = f1
                        results["Best Precision"] = precision
                        results["Best Recall"] = recall
                        results["Best Threshold"] = threshold
                        results["Positive Predictions Count"] = positive_predictions

            elif hasattr(model, "predict"):
                # Das Modell unterstützt nur `predict`
                y_pred = model.predict(X)
                positive_predictions = (y_pred == 1).sum()

                if positive_predictions < min_positive_predictions:
                    precision, recall, f1 = 0.0, 0.0, 0.0
                else:
                    precision = precision_score(y, y_pred, pos_label=1, zero_division=0)
                    recall = recall_score(y, y_pred, pos_label=1, zero_division=0)
                    f1 = f1_score(y, y_pred, pos_label=1, zero_division=0)

                # Aktualisiere Ergebnisse
                results["Best Precision"] = precision
                results["Best Recall"] = recall
                results["Best F1-Score"] = f1
                results["Positive Predictions Count"] = positive_predictions
                results["Details"].append({
                    "Threshold": None,
                    "Precision": precision,
                    "Recall": recall,
                    "F1-Score": f1,
                    "Positive Predictions Count": positive_predictions
                })

            else:
                raise AttributeError("Das Modell muss entweder `predict_proba` oder `predict` unterstützen.")

            return results


        custom_scorer = make_scorer(self.custom_scoring, greater_is_better=True)

        param_grid = {}

        results = {}
        for model_name, (model, param_grid) in models.items():
            print(f"Training {model_name}...")

            # Hole die verschiedenen Pipeline-Varianten
            pipeline_variants = self.get_pipeline_variants(model)

            for i, pipeline in enumerate(pipeline_variants):
                print(f"\nTesting pipeline variant {i + 1} for {model_name}")

                random_search = RandomizedSearchCV(
                    estimator=pipeline,
                    param_distributions=param_grid,
                    n_iter=66,
                    cv=tscv,
                    verbose=0,
                    n_jobs=3,
                    random_state=42
                )

                # Führe RandomizedSearch durch und speichere das beste Modell
                random_search.fit(X_train, y_train)

                best_cv_score = random_search.best_score_
                best_model = random_search.best_estimator_

                train_result = evaluate_model(best_model, X_train, y_train,
                                                                       thresholds=np.arange(0.45, 0.95, 0.05).tolist())
                test_result = evaluate_model(best_model, X_test, y_test,
                                                                     thresholds=np.arange(0.45, 0.95, 0.05).tolist())

                print(
                    f"Model: {model_name} - Variant {i + 1}, CV: {best_cv_score:.4f}, {test_result}"
                )
                results[f"{model_name} - Variant {i + 1}"] = (test_result["Best F1-Score"], best_model)

        # Ausgabe des besten Modells basierend auf Test-Precision
        best_model_name = max(results, key=lambda k: results[k][0])
        best_test_precision, best_model = results[best_model_name]

        print(f"\nBest Model: {best_model_name} with Test Precision: {best_test_precision:.4f}")
        return best_model, best_test_precision

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
    def evaluate_model(model, X, y, thresholds=None, min_positive_predictions=10):
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
            "Best Threshold": None,
            "Positive Predictions Count": 0,
            "Details": []  # Detaillierte Ergebnisse für jeden Schwellenwert
        }

        if hasattr(model, "predict_proba"):
            # Das Modell unterstützt `predict_proba`
            y_proba = model.predict_proba(X)[:, 1]

            for threshold in thresholds:
                y_pred_thresholded = (y_proba >= threshold).astype(int)
                positive_predictions = y_pred_thresholded.sum()

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
                    "F1-Score": f1,
                    "Positive Predictions Count": positive_predictions
                })

                # Aktualisiere die besten Metriken basierend auf dem F1-Score
                if f1 > results["Best F1-Score"]:
                    results["Best F1-Score"] = f1
                    results["Best Precision"] = precision
                    results["Best Recall"] = recall
                    results["Best Threshold"] = threshold
                    results["Positive Predictions Count"] = positive_predictions

        elif hasattr(model, "predict"):
            # Das Modell unterstützt nur `predict`
            y_pred = model.predict(X)
            positive_predictions = (y_pred == 1).sum()

            if positive_predictions < min_positive_predictions:
                precision, recall, f1 = 0.0, 0.0, 0.0
            else:
                precision = precision_score(y, y_pred, pos_label=1, zero_division=0)
                recall = recall_score(y, y_pred, pos_label=1, zero_division=0)
                f1 = f1_score(y, y_pred, pos_label=1, zero_division=0)

            # Aktualisiere Ergebnisse
            results["Best Precision"] = precision
            results["Best Recall"] = recall
            results["Best F1-Score"] = f1
            results["Positive Predictions Count"] = positive_predictions
            results["Details"].append({
                "Threshold": None,
                "Precision": precision,
                "Recall": recall,
                "F1-Score": f1,
                "Positive Predictions Count": positive_predictions
            })

        else:
            raise AttributeError("Das Modell muss entweder `predict_proba` oder `predict` unterstützen.")

        return results






    def feature_importance(self, merged_df) -> List:
        X = merged_df.drop(columns=["chart_index", "result"])
        y = merged_df['result']

        # Random Forest Modell
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X, y)

        # Feature Importance
        feature_importances = pd.Series(model.feature_importances_, index=X.columns)
        feature_importances = feature_importances.sort_values(ascending=False)

        # Visualisierung der Feature-Wichtigkeiten
        # plt.figure(figsize=(12, 6))
        # sns.barplot(x=feature_importances, y=feature_importances.index)
        # plt.title("Feature-Importance basierend auf Random Forest")
        # plt.xlabel("Feature-Importance Score")
        # plt.show()

        correlation_matrix = X.corr().abs()
        upper_triangle = correlation_matrix.where(np.triu(np.ones(correlation_matrix.shape), k=1).astype(bool))
        high_correlation_features = [column for column in upper_triangle.columns if any(upper_triangle[column] > 0.9)]
        print(f"Highly correlated features: {high_correlation_features}")


        selector = VarianceThreshold(threshold=0.01)
        selector.fit(X)
        low_variance_features = [column for column in X.columns if column not in X.columns[selector.get_support()]]
        print(f"Low variance features: {low_variance_features}")

        bad_features = feature_importances[feature_importances < 0.01]
        return bad_features.index.tolist() + high_correlation_features + low_variance_features
