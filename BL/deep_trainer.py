# region import
from typing import List
import numpy as np
from sklearn.feature_selection import VarianceThreshold
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score
from sklearn.ensemble import RandomForestClassifier
import pandas as pd
from tensorflow.keras.optimizers import RMSprop
from tensorflow.keras.regularizers import l2
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.callbacks import EarlyStopping


# endregion

class DeepTrainer:

    def train(self, df) -> (RandomForestClassifier, float):
        rf, accuracy = self._train_random_forest(df)

        #_, accuracy_with_less_features = self._train_random_forest(df.drop(columns=self.feature_importance(df)))

        #if accuracy_with_less_features > accuracy:
        #    print(f"!Warning: Accuracy with less features {accuracy_with_less_features} "
        #          f"is better than with all features {accuracy}!")

        return rf, accuracy

    def _train_random_forest(self, df) -> (RandomForestClassifier, float):
        # Vorbereiten der Features und Zielvariable
        df = df.drop('chart_index', axis=1)
        _X = df.drop(columns=['result'])  # Features: Alle Spalten außer 'result'
        y = df['result']  # Zielvariable

        # Splitte die Daten in Trainings- und Testdaten (80% Training, 20% Test)
        _X_train, _X_test, y_train, y_test = train_test_split(_X, y, test_size=0.2, stratify=y, random_state=42)

        # Hyperparameter-Raster
        param_grid = {
            'classifier__n_estimators': [50, 100, 200],  # Anzahl der Bäume im Wald
            'classifier__max_depth': [None, 10, 20, 30],  # Maximale Tiefe der Bäume
            'classifier__min_samples_split': [2, 5, 10],  # Mindestanzahl von Samples, um einen Knoten zu splitten
            'classifier__min_samples_leaf': [1, 2, 4],  # Mindestanzahl von Samples in einem Blatt
            'classifier__max_features': ['sqrt'],  # Anzahl der Merkmale, die beim Splitten berücksichtigt werden
            'classifier__bootstrap': [True, False],  # Ob Bootstrap-Sampling verwendet werden soll
            'classifier__criterion': ['gini', 'entropy'],  # Split-Kriterium
            'classifier__class_weight': ['balanced', None],  # Gewichtung der Klassen
        }

        # Pipeline: Optionaler StandardScaler und RandomForestClassifier
        pipeline = Pipeline([
            ('scaler', StandardScaler()),  # Skaliere nur, wenn nötig
            ('classifier', RandomForestClassifier(random_state=42))
        ])

        # Stratified K-Fold für stabilere Kreuzvalidierung bei Klassenungleichgewicht
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

        # RandomizedSearchCV mit reduzierten Parametern
        random_search = RandomizedSearchCV(
            estimator=pipeline,
            param_distributions=param_grid,
            n_iter=50,
            cv=cv,
            verbose=0,
            n_jobs=-1,
            random_state=42
        )

        # Suche starten
        random_search.fit(_X_train, y_train)

        # Beste cross-validation accuracy und Testgenauigkeit anzeigen
        print("Best Score:", random_search.best_score_)
        self.analyze_cv_scores(random_search.cv_results_['mean_test_score'])

        best_model = random_search.best_estimator_

        # Test-Genauigkeit des besten Modells
        y_prediction = best_model.predict(_X_test)
        test_accuracy = accuracy_score(y_test, y_prediction)

        print("Test accuracy with best parameters:", test_accuracy)

        # Optionale Validierungsfunktion für weitere Auswertung
        self.validate_model(best_model, _X_test, y_test)

        return best_model, test_accuracy

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
    def validate_model(model, X, y):
        predictions = model.predict(X)
        predictions_binary = (predictions > 0.5).astype(int)  # Schwellenwert 0.5
        train_df_new = X.copy()

        train_df_new['predicted_profit'] = predictions_binary
        train_df_new['result'] = y
        train_df_new = train_df_new[train_df_new['predicted_profit'] == 1]
        accuracy = (train_df_new['predicted_profit'] == train_df_new['result']).mean()
        print(f"++++++++++++++++++++++Genauigkeit: {accuracy * 100:.2f}%")

    def train_and_save_model(self,df, model_path='trading_model.h5'):
        # Spalten "Profit" muss die Zielvariable sein

        df = df.drop('chart_index', axis=1)
        X = df.drop(columns=['result'])  # Features: Alle Spalten außer 'Profit'
        y = df['result']  # Zielvariable: Spalte 'Profit'

        # Splitte die Daten in Trainings- und Testdaten (80% Training, 20% Test)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Erstelle das neuronale Netzwerk
        model = Sequential([
            Dense(16, activation='relu', kernel_regularizer=l2(0.01), input_shape=(X_train.shape[1],)),
            Dropout(0.2),  # 30% der Neuronen werden zufällig deaktiviert
            Dense(8, activation='relu', kernel_regularizer=l2(0.01)),
            Dropout(0.2),
            Dense(1, activation='sigmoid')  # Sigmoid für binäre Klassifikation
        ])

        # Modell kompilieren
        model.compile(optimizer=RMSprop(learning_rate=0.0005), loss='binary_crossentropy', metrics=['accuracy'])

        # Early stopping
        early_stopping = EarlyStopping(monitor='val_loss', patience=8, restore_best_weights=True)

        # Modell trainieren
        history = model.fit(X_train, y_train, validation_data=(X_test, y_test), epochs=100, batch_size=32,
                            callbacks=[early_stopping])

        # Zugriff auf val_loss und val_accuracy
        val_loss = history.history['val_loss'][-1]
        val_accuracy = history.history['val_accuracy'][-1]

        # Modell speichern
        print(f"Accurace {val_accuracy}")
        return model

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
