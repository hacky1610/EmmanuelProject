# region import
import warnings
from pytorch_tabnet.tab_model import TabNetClassifier
import numpy as np
import pandas as pd
import tensorflow as tf
from imblearn.over_sampling import SMOTE
from keras import Sequential, Input, Model
from keras.src.callbacks import ReduceLROnPlateau, EarlyStopping
from keras.src.layers import Dense, Dropout, BatchNormalization, Add, Reshape, Conv1D, MaxPooling1D, Flatten
from keras.src.optimizers import Adam, SGD, RMSprop, AdamW
from lightgbm import LGBMClassifier
from pandas import DataFrame
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.metrics import make_scorer, precision_score
from sklearn.metrics import recall_score, f1_score
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler
from statsmodels.stats.outliers_influence import variance_inflation_factor
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
            # # }),
            #     'Gradient Boosting': (GradientBoostingClassifier(random_state=42), {
            #         'classifier__n_estimators': [50, 100, 200],
            #         'classifier__max_depth': [3, 5, 7],
            #         'classifier__learning_rate': [0.01, 0.1, 0.2],
            #     }),
            # 'Random Forest Balanced': (RandomForestClassifier(random_state=42, class_weight='balanced'), {
            #     'classifier__n_estimators': [50, 100, 200],
            #     'classifier__max_depth': [10, 20],
            #     'classifier__min_samples_split': [2, 5],
            #     'classifier__min_samples_leaf': [1, 2, 4],
            #     'classifier__max_features': ['sqrt'],
            #     'classifier__bootstrap': [True, False],
            # }),
            # 'XGBoost Simple': (XGBClassifier(random_state=42, use_label_encoder=False, eval_metric='logloss', verbosity=0), {
            #     'classifier__max_depth': [3, 5],  # Explore shallower to deeper trees
            # }),

            # 'XGBoost': (XGBClassifier(random_state=42, use_label_encoder=False, eval_metric='logloss',  verbosity=0), {
            #        'classifier__max_depth': [3, 5, 7, 10, 12],             # Explore shallower to deeper trees
            #         'classifier__learning_rate': [0.01, 0.05, 0.1, 0.2],   # Test smaller learning rates
            #         'classifier__n_estimators': [50, 100, 200, 300, 500],   # Cover a wider range of estimators
            #         'classifier__subsample': [0.6, 0.8, 1.0],               # Tweak sampling rate to control overfitting
            #         'classifier__colsample_bytree': [0.6, 0.8, 1.0]         # Contr
            # }),

            # 'Random Forest Balanced Weighted': (RandomForestClassifier(random_state=42, class_weight={0: 1, 1: 10}), {
            #     'classifier__n_estimators': [50, 100, 200],
            #     'classifier__max_depth': [10, 20],
            #     'classifier__min_samples_split': [2, 5],
            #     'classifier__min_samples_leaf': [1, 2, 4],
            #     'classifier__max_features': ['sqrt'],
            #     'classifier__bootstrap': [True, False],
            # }),
            # 'LightGBM': (lgb.LGBMClassifier(random_state=42, verbose=-1),
            #              {
            #                  'classifier__max_depth': [3, 5, 7, 10, 12],
            #                  # Ähnlich wie XGBoost, tiefere und flachere Bäume testen
            #                  'classifier__learning_rate': [0.01, 0.05, 0.1, 0.2],  # Geringere Lernraten ausprobieren
            #                  'classifier__n_estimators': [50, 100, 200, 300, 500],
            #                  # Größerer Bereich für die Anzahl der Bäume
            #                  'classifier__subsample': [0.6, 0.8, 1.0],
            #                  # Sampling-Rate zum Überanpassungskontrolle anpassen
            #                  'classifier__colsample_bytree': [0.6, 0.8, 1.0]  # Anteil der Spalten für Baumaufbau
            #              }),
        #     'LightGBM Weighted (is_unbalance)': (
        #     lgb.LGBMClassifier(random_state=42, is_unbalance=True, verbose=-1),
        #     {
        #         'classifier__max_depth': [3, 5, 7],
        #         'classifier__learning_rate': [0.01, 0.1],
        #         'classifier__n_estimators': [100, 200],
        #         'classifier__subsample': [0.8, 1.0],
        #         'classifier__colsample_bytree': [0.8, 1.0],
        #     }
        # ),
        #     'LightGBM Weighted (scale_pos_weight)': (
        #         lgb.LGBMClassifier(random_state=42, verbose=-1),
        #         {
        #             'classifier__max_depth': [3, 5, 7],
        #             'classifier__learning_rate': [0.01, 0.1],
        #             'classifier__n_estimators': [100, 200],
        #             'classifier__subsample': [0.8, 1.0],
        #             'classifier__colsample_bytree': [0.8, 1.0],
        #             'classifier__scale_pos_weight': [5, 10, 20],  # Experimentiere mit Werten
        #         }
        #     ),
        #     'CatBoost': (CatBoostClassifier(random_seed=42, verbose=0),
        #                  {
        #                      'classifier__depth': [3, 5, 7, 10, 12],  # Baumtiefe
        #                      'classifier__learning_rate': [0.01, 0.05, 0.1, 0.2],  # Lernrate
        #                      'classifier__iterations': [50, 100, 200, 300, 500],
        #                      # Anzahl der Iterationen (entspricht n_estimators)
        #                      'classifier__subsample': [0.6, 0.8, 1.0],  # Sampling-Rate
        #                      'classifier__colsample_bylevel': [0.6, 0.8, 1.0]  # Anteil der Spalten auf Ebene
        #                  }),
        #     'CatBoost Weighted': (CatBoostClassifier(random_seed=42, verbose=0, class_weights=[1, 10]), {
        #         'classifier__depth': [3, 5, 7],
        #         'classifier__learning_rate': [0.01, 0.1],
        #         'classifier__iterations': [100, 200],
        #         'classifier__subsample': [0.8, 1.0],
        #     }),
        #     'Keras':  (KerasWrapper(), {
        #             'classifier__dropout_rate': [0.2, 0.3, 0.5],
        #         'classifier__optimizer': ['adam', 'sgd', 'rmsprop', "adamw"],
        #         'classifier__learning_rate': [0.001, 0.01, 0.1],
        #         'classifier__epochs': [50, 100, 200],
        #         'classifier__batch_size': [32, 64, 128],
        #         'classifier__activation': ['relu', 'tanh', 'elu'],
        #         'classifier__model_type': ['V1', 'V2', 'V3','V4', 'V5'],
        #         'classifier__initializer': ['he_normal', 'glorot_uniform', 'lecun_normal']
        #     }),

            'XGBoost Weighted': (
                XGBClassifier(random_state=42, use_label_encoder=False, eval_metric='logloss', verbosity=0), {
                    'classifier__max_depth': [3, 5, 7],
                    'classifier__learning_rate': [0.01, 0.1, 0.2],
                    'classifier__gamma': [0, 0.1, 0.5, 1],
                    'classifier__colsample_bytree': [0.8, 1.0],
                    'classifier__min_child_weight': [1, 5, 10],  # Minimale Anforderungen an Split
                    'classifier__scale_pos_weight': [0.15, 0.3, 0.5, 0.7, 1.0],
                    'classifier__n_estimators': [50, 100, 200, 300],
                    'classifier__subsample': [0.6, 0.8, 1.0],
                    'classifier__reg_alpha': [0, 0.1, 0.5, 1],
                    'classifier__reg_lambda': [1, 1.5, 2, 5],
                    'classifier__max_leaves': [31, 63, 127],  # Für loss guide Wachstum
                    'classifier__grow_policy': ['depthwise', 'lossguide']
                }),
            # 'LGBM Weighted': (
            #     LGBMClassifier(random_state=42, objective='binary', is_unbalance=True), {
            #         'classifier__max_depth': [-1, 5, 10, 20],  # -1 bedeutet keine Begrenzung
            #         'classifier__learning_rate': [0.01, 0.05, 0.1],
            #         'classifier__n_estimators': [50, 100, 200, 500],
            #         'classifier__num_leaves': [31, 63, 127],  # Kontrolliert die Baumkomplexität
            #         'classifier__min_child_samples': [10, 20, 50],  # Mindestanzahl an Samples in einem Blatt
            #         'classifier__subsample': [0.6, 0.8, 1.0],
            #         'classifier__colsample_bytree': [0.6, 0.8, 1.0],
            #         'classifier__reg_alpha': [0.0, 0.1, 0.5, 1.0],  # L1 Regularisierung
            #         'classifier__reg_lambda': [0.0, 0.1, 0.5, 1.0],  # L2 Regularisierung
            #         'classifier__scale_pos_weight': [0.5, 1, 2],  # Für unbalancierte Daten
            #     }
            # ),

            # 'TabNet': (
            #     TabNetClassifier(seed=42), {
            #         'classifier__n_d': [8, 16, 32],  # Dimensionen des Entscheidungs-Layers
            #         'classifier__n_a': [8, 16, 32],  # Dimensionen des Attentions-Layers
            #         'classifier__n_steps': [3, 5, 7],  # Schritte im Entscheidungsprozess
            #         'classifier__gamma': [1.0, 1.5, 2.0],  # Verlustgewichtung
            #         'classifier__lambda_sparse': [0.001, 0.01, 0.1],  # Regularisierung für Sparsity
            #         'classifier__momentum': [0.02, 0.04, 0.1],  # Momentumbasierte Optimierung
            #     }
            # )


        #     'CatBoost Weighted 2': (CatBoostClassifier(random_seed=42, verbose=0, class_weights=[10, 1]), {
        #         'classifier__depth': [3, 5, 7],
        #         'classifier__learning_rate': [0.01, 0.1],
        #         'classifier__iterations': [100, 200],
        #         'classifier__subsample': [0.8, 1.0],
        #     }),

            # 'Logistic Regression': (LogisticRegression(random_state=42, max_iter=1000), {
            #     'classifier__C': [0.1, 1, 10],
            #     'classifier__penalty': ['l2'],
            #     'classifier__solver': ['lbfgs', 'saga'],
            # }),
            # 'Logistic Regression Weighted': (
            # LogisticRegression(random_state=42, max_iter=1000, class_weight={0: 1, 1: 10}), {
            #     'classifier__C': [0.1, 1, 10],
            #     'classifier__penalty': ['l2'],
            #     'classifier__solver': ['lbfgs', 'saga'],
            # }),
            # 'Logistic Regression Weighted 2': (
            #     LogisticRegression(random_state=42, max_iter=1000, class_weight={0: 10, 1: 1}), {
            #         'classifier__C': [0.1, 1, 10],
            #         'classifier__penalty': ['l2'],
            #         'classifier__solver': ['lbfgs', 'saga'],
            #     }),

            # 'Support Vector Machine': (SVC(probability=True, random_state=42), {
            #     'classifier__C': [0.1, 1, 10],
            #     'classifier__kernel': ['linear', 'rbf'],
            #     'classifier__gamma': ['scale', 'auto'],
            # }),
            # 'Support Vector Machine Weighted': (SVC(probability=True, random_state=42, class_weight={0: 1, 1: 10}), {
            #     'classifier__C': [0.1, 1, 10],
            #     'classifier__kernel': ['linear', 'rbf'],
            #     'classifier__gamma': ['scale', 'auto'],
            # }),
            #
            # 'Support Vector Machine Weighted 2': (SVC(probability=True, random_state=42, class_weight={0: 10, 1: 1}), {
            #     'classifier__C': [0.1, 1, 10],
            #     'classifier__kernel': ['linear', 'rbf'],
            #     'classifier__gamma': ['scale', 'auto'],
            # }),
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

    def evaluate_features(self, df, target, quantile=0.75, min_feature_factor=0.1):
        # 1. Korrelation mit Zielwert berechnen
        correlation = self.correlation_with_target(df, target, )
        # 2. Feature-Importance mit RandomForest berechnen
        importance_df = self.feature_importance(df, target)

        # 3. VIF (Variance Inflation Factor) berechnen
        vif_df = self.calculate_vif(df.drop(columns=[target]))
        top_vif = vif_df.sort_values(by='VIF', ascending=False).head(15)

        correlation_matrix = df.corr()
        for a, b in top_vif.iterrows():
            correlated_features = correlation_matrix[b.Variable].sort_values(ascending=False)
            # print(f"\nFeatures, die stark mit {b.Variable} korrelieren:")
            # print(correlated_features[abs(correlated_features) > 0.8])

        # Kombinierte Score-Berechnung: Korrelation + Feature-Importance - (1/VIF)
        combined_scores = pd.DataFrame({
            'Feature': df.columns,
            'Correlation': correlation,
            'Importance': importance_df.set_index('Feature')['Importance'].reindex(df.columns).fillna(0),
        })

        # VIF hinzufügen und kombinierte Bewertung berechnen (niedrigere VIF-Werte besser, daher invertiert)
        combined_scores['VIF'] = combined_scores['Feature'].map(vif_df.set_index('Variable')['VIF'])
        combined_scores['Score'] = combined_scores['Correlation'] + combined_scores['Importance']
        combined_scores = combined_scores.sort_values('Score', ascending=False)
        high_score_threshold = combined_scores['Score'].quantile(quantile)
        top_features = combined_scores[combined_scores['Score'] > high_score_threshold]

        #remove result
        top_features = top_features[top_features["Feature"] != "result"]
        m = MinMaxScaler(feature_range=(min_feature_factor, 1))
        top_features["Score_transformed"] = m.fit_transform(top_features[["Score"]])

        return top_features

    def correlation_with_target(self, df, target):
        correlation = df.corr()[target]
        return correlation

    def calculate_vif(self, df):
        vif_data = pd.DataFrame()
        vif_data['Variable'] = df.columns
        vif_data['VIF'] = [variance_inflation_factor(df.values, i) for i in range(df.shape[1])]
        return vif_data

    def feature_importance(self, df, target):
        # Features und Ziel trennen
        X = df.drop(columns=[target])
        y = df[target]

        # RandomForest-Modell trainieren
        model = RandomForestClassifier(random_state=42)
        model.fit(X, y)

        # Feature-Importances extrahieren
        importance_df = pd.DataFrame({
            'Feature': X.columns,
            'Importance': model.feature_importances_
        }).sort_values(by='Importance', ascending=False)

        return importance_df

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
    def _train_model(self, pipeline_index, model_name, pipeline, param_grid, tscv,
                     X_train, y_train, X_test, y_test, feature_factors:DataFrame,
                     quantile, hours, iterations, evaluate_type, min_feature_factor):
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
                                      thresholds=np.arange(0.45, 0.95, 0.05).tolist(), evaluate_type=evaluate_type, min_positive_predictions=100)
        test_result = self.evaluate_model(best_model, X_test, y_test,
                                     thresholds=[train_result["Best Threshold"]], evaluate_type=evaluate_type, min_positive_predictions=15)

        retest_test_dict = {}
        if test_result["Best Precision"] >= 0.65:
            print("Test-Ergebnisse sehen gut aus. Modell wird jetzt auf dem gesamten Dataset trainiert.")

            # Gesamtes Dataset kombinieren
            X_full = pd.concat([X_train, X_test])
            y_full = pd.concat([y_train, y_test])

            # Modell mit besten Parametern erneut trainieren
            best_model.fit(X_full, y_full)

            retest_test_result = self.evaluate_model(best_model, X_full, y_full,
                                              thresholds=[train_result["Best Threshold"]], evaluate_type=evaluate_type,
                                              min_positive_predictions=100)

            retest_test_dict = {
                "Retest Precision": retest_test_result["Best Precision"],
                "Retest F1": retest_test_result["Best F1-Score"],
                "Retest Recall": retest_test_result["Best Recall"],
                "Positive Predictions Count": retest_test_result["Positive Predictions Count"],
                "Retest Reward": retest_test_result["Reward"],
            }

            print("Das Modell wurde erfolgreich auf dem gesamten Dataset trainiert.")


        return random_search.best_params_ | {
            "Model": model_name,
            "Pipeline Variant": pipeline_index + 1,
            "CV Score": best_cv_score,
            "Trading Houres": hours,
            "Evaluate Type": evaluate_type,
            "Min Feature Factor": min_feature_factor,
            "Score": (train_result["Best Precision"] + best_cv_score) / 2,
            "Best Precision": test_result["Best Precision"],
            "Best Recall": test_result["Best Recall"],
            "Best F1-Score": test_result["Best F1-Score"],
            "Best Threshold": test_result["Best Threshold"],
            "Positive Predictions Count": test_result["Positive Predictions Count"],
            "Best Reward": test_result["Reward"],
            "Best Train Precision": train_result["Best Precision"],
            "Best Train Recall": train_result["Best Recall"],
            "Best Train F1-Score": train_result["Best F1-Score"],
            "Best Train Threshold": train_result["Best Threshold"],
            "Best Train Reward": train_result["Reward"],
            "Positive Predictions Count Train": train_result["Positive Predictions Count"],
            "Best Model": best_model,
            "Feature Factors": feature_factors,
            "Quantile": quantile,
            "Iterations": iterations
        } | retest_test_dict



    def train(self, df, hours, quantile, iterations, evaluate_type,min_feature_factor):
        # Suppress warnings
        warnings.filterwarnings("ignore")

        df = df.drop(columns=["chart_index"])
        # Split dataset into training and test sets
        df_train = df[:int(len(df) * 0.9)]
        df_test = df[int(len(df) * 0.9):]

        good_features_df = self.evaluate_features(df_train, "result", quantile, min_feature_factor)
        selected_features = (
            good_features_df.sort_values(by="Score", ascending=False)  # Nach Scores sortieren
            .index  # Feature-Namen
            .tolist()  # Als Liste extrahieren
        )


        X_train = df_train.drop(columns=['result'])[selected_features]
        X_test = df_test.drop(columns=['result'])[selected_features]

        y_train = df_train['result']
        y_test = df_test['result']

        factors = good_features_df["Score_transformed"]

        # Werte in `X_train` mit den entsprechenden Faktoren multiplizieren
        X_train = X_train.multiply(factors, axis=1)
        X_test = X_test.multiply(factors, axis=1)

        # Apply SMOTE only on the training set
        smote = SMOTE(random_state=42)
        X_train, y_train = smote.fit_resample(X_train, y_train)

        # Models and parameter grids
        models = self._get_models()

        # Cross-validation
        tscv = TimeSeriesSplit(n_splits=5)
        best_results = []


        for model_name, (model, param_grid) in models.items():
            print(f"Training {model_name}...")

            # Hole die verschiedenen Pipeline-Varianten
            pipeline_variants = self.get_pipeline_variants(model)

            for i, pipeline in enumerate(pipeline_variants):
                res = self._train_model(pipeline_index=i, model_name=model_name, pipeline=pipeline,
                                        param_grid=param_grid, tscv=tscv, X_train=X_train, y_train=y_train,
                                        X_test=X_test, y_test=y_test, feature_factors=factors,
                                        quantile=quantile, hours=hours, iterations=iterations,
                                        evaluate_type=evaluate_type, min_feature_factor=min_feature_factor)

                best_results.append(res)


        # Ausgabe des besten Modells basierend auf Test-Precision
        #best_model_name = max(results, key=lambda k: results[k][0])
        #best_test_precision, best_model = results[best_model_name]

        best_item = max(best_results, key=lambda x: x['Score'])
        print(f"Precision {best_item['Best Precision']} from {best_item['Model']}")
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
            min_positive_predictions: Minimale Anzahl an positiven Vorhersagen, um Metriken zu berücksichtigen.
            evaluate_type: Metrik zur Optimierung, entweder "f1" oder "precision".

        Returns:
            Dictionary mit den besten Metriken und weiteren Informationen.
        """
        if thresholds is None:
            thresholds = [0.5]  # Standard-Schwellenwert

        # Initialisiere Ergebnisse
        results = {
            "Best Precision": -1,
            "Best Recall": -1,
            "Best F1-Score": -1,
            "Best Threshold": 0.5,
            "Positive Predictions Count": -1,
            "Reward": -1,
            "Details": []  # Detaillierte Ergebnisse für jeden Schwellenwert
        }

        # Vorhersagenwahrscheinlichkeiten
        y_proba = model.predict_proba(X)[:, 1]
        valid_results = []  # Ergebnisse, die min_positive_predictions erfüllen

        for threshold in thresholds:
            y_pred_thresholded = (y_proba >= threshold).astype(int)
            positive_predictions = y_pred_thresholded.sum()

            true_positives = ((y_pred_thresholded == 1) & (y == 1)).sum()
            false_positives = ((y_pred_thresholded == 1) & (y == 0)).sum()
            tp_minus_fp = true_positives - false_positives

            precision = precision_score(y, y_pred_thresholded, pos_label=1, zero_division=0)
            recall = recall_score(y, y_pred_thresholded, pos_label=1, zero_division=0)
            f1 = f1_score(y, y_pred_thresholded, pos_label=1, zero_division=0)

            result = {
                "Threshold": threshold,
                "Precision": precision,
                "Recall": recall,
                "F1-Score": f1,
                "Positive Predictions Count": positive_predictions,
                "Reward": tp_minus_fp
            }

            results["Details"].append(result)

            if positive_predictions >= min_positive_predictions:
                valid_results.append(result)

        # Wähle das beste Ergebnis aus valid_results oder alle Ergebnisse
        if valid_results:
            candidates = valid_results
        else:
            candidates = results["Details"]

        for candidate in candidates:
            if evaluate_type == "f1":
                if candidate["F1-Score"] > results["Best F1-Score"]:
                    results.update({
                        "Best F1-Score": candidate["F1-Score"],
                        "Best Precision": candidate["Precision"],
                        "Best Recall": candidate["Recall"],
                        "Best Threshold": candidate["Threshold"],
                        "Positive Predictions Count": candidate["Positive Predictions Count"],
                        "Reward": candidate["Reward"]
                    })
            elif evaluate_type == "precision":
                if candidate["Precision"] > results["Best Precision"]:
                    results.update({
                        "Best F1-Score": candidate["F1-Score"],
                        "Best Precision": candidate["Precision"],
                        "Best Recall": candidate["Recall"],
                        "Best Threshold": candidate["Threshold"],
                        "Positive Predictions Count": candidate["Positive Predictions Count"],
                        "Reward": candidate["Reward"]
                    })

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







