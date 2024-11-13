# region import
import warnings
from typing import List
import numpy as np
from imblearn.over_sampling import SMOTE
from sklearn.decomposition import PCA
from sklearn.feature_selection import VarianceThreshold, SelectKBest, f_classif, SelectFromModel
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, TimeSeriesSplit, GridSearchCV
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score
from sklearn.metrics import make_scorer, precision_score
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier, VotingClassifier, GradientBoostingClassifier
import pandas as pd
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, PolynomialFeatures, MinMaxScaler
from xgboost import XGBClassifier


# endregion

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
        pipeline_variants = [
            Pipeline([
                ('scaler', MinMaxScaler()),  # Variante 1: MinMaxScaler
                ('classifier', model)
            ]),
            Pipeline([
                ('scaler', StandardScaler()),  # Variante 2: StandardScaler
                ('classifier', model)
            ]),
            Pipeline([
                ('scaler', MinMaxScaler()),  # Variante 3: MinMaxScaler + PCA
                ('pca', PCA(n_components=10)),
                ('classifier', model)
            ]),
            Pipeline([
                ('scaler', StandardScaler()),  # Variante 4: StandardScaler + PCA
                ('pca', PCA(n_components=10)),
                ('classifier', model)
            ]),
            Pipeline(
            [('scaler', MinMaxScaler()),
             ('feature_selection_model', SelectFromModel(RandomForestClassifier(n_estimators=50, random_state=42))),
            ('classifier', model)]),
            Pipeline(
                [('scaler', MinMaxScaler()),
                 ('variance_threshold', VarianceThreshold(threshold=0.0)),
                 ('classifier', model)])
        ]

    def _train_random_forest(self, df):
        # Suppress warnings
        warnings.filterwarnings("ignore")

        # Split dataset into training and test sets
        df_train = df[:int(len(df) * 0.9)]
        df_test = df[int(len(df) * 0.9):]
        X_train, y_train = df_train.drop(columns=['result']), df_train['result']
        X_test, y_test = df_test.drop(columns=['result']), df_test['result']

        # Apply SMOTE only on the training set
        smote = SMOTE(random_state=42)
        X_train, y_train = smote.fit_resample(X_train, y_train)

        # Models and parameter grids
        models = {
            'Random Forest': (RandomForestClassifier(random_state=42), {
                'classifier__n_estimators': [100, 200, 300],
                'classifier__max_depth': [10, 20],
            }),
            'Gradient Boosting': (GradientBoostingClassifier(random_state=42), {
                'classifier__n_estimators': [50, 100, 200],
                'classifier__max_depth': [3, 5, 7],
                'classifier__learning_rate': [0.01, 0.1, 0.2],
            }),
            # Add other models similarly
        }

        # Cross-validation
        tscv = TimeSeriesSplit(n_splits=5)

        def evaluate_model(model, X, y, thresholds, min_positive_predictions=10) -> float:
            y_proba = model.predict_proba(X)[:, 1]
            best_threshold, best_precision = 0.5, 0.0
            for threshold in thresholds:
                y_pred_thresholded = (y_proba >= threshold).astype(int)
                positive_predictions = y_pred_thresholded.sum()

                # Überprüfe, ob die Anzahl positiver Vorhersagen das Minimum erreicht
                if positive_predictions < min_positive_predictions:
                    # Rückgabe von 0, wenn zu wenige positive Vorhersagen gemacht wurden
                    precision = 0.0
                else:
                    print(f"Positive Predictions: {positive_predictions}")
                    precision = precision_score(y, y_pred_thresholded, pos_label=1, zero_division=0)
                if precision > best_precision:
                    best_precision, best_threshold = precision, threshold
            return best_precision, best_threshold


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

                train_precision, best_train_threshold = evaluate_model(best_model, X_train, y_train,
                                                                       thresholds=np.arange(0.45, 0.95, 0.05).tolist())
                test_precision, best_test_threshold = evaluate_model(best_model, X_test, y_test,
                                                                     thresholds=np.arange(0.45, 0.95, 0.05).tolist())

                print(
                    f"Model: {model_name} - Variant {i + 1}, CV: {best_cv_score:.4f}, Train Threshold: {best_train_threshold}, Test Precision : {test_precision:.4f} - {best_test_threshold}"
                )
                results[f"{model_name} - Variant {i + 1}"] = (test_precision, train_precision, best_model)

        # Ausgabe des besten Modells basierend auf Test-Precision
        best_model_name = max(results, key=lambda k: results[k][0])
        best_test_precision, train_precision, best_model = results[best_model_name]

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
    def validate_model(model, X_test, y_test, thresholds=[0.5, 0.6, 0.7, 0.8, 0.9]):
        best_pred = 0
        for threshold in thresholds:
            y_pred = DeepTrainer.conservative_predict(model, X_test, threshold)

            # Anzahl der Vorhersagen mit 1 und wie viele korrekt waren
            total_pred_1 = np.sum(y_pred)
            correct_pred_1 = np.sum((y_pred == 1) & (y_test == 1))

            print(f"Anzahl der '1'-Vorhersagen: {total_pred_1}")
            print(f"Erfolgreiche '1'-Vorhersagen: {correct_pred_1}")

            print("-" * 40)

            pred_acc = correct_pred_1  / total_pred_1 if total_pred_1 > 0 else 0
            if pred_acc > best_pred:
                best_pred = pred_acc

            print(f"Accuracy: {pred_acc}")

        return best_pred






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
