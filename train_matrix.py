# region import
import os
import random
import traceback
from sklearn.model_selection import ParameterSampler
from itertools import combinations
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import RandomizedSearchCV
from typing import Type
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
import dropbox
import pymongo
import pandas as pd
from pandas import DataFrame
from tensorflow.keras.optimizers import Adam, RMSprop
from BL.analytics import Analytics
from BL.data_processor import DataProcessor
from BL.indicators import Indicators
from BL.utils import ConfigReader, EnvReader
from Connectors.IG import IG
from sklearn.model_selection import cross_val_score
from Connectors.dropbox_cache import DropBoxCache
from Connectors.dropboxservice import DropBoxService
from Connectors.market_store import MarketStore
from Connectors.predictore_store import PredictorStore
from Connectors.tiingo import TradeType, Tiingo
from Predictors.generic_predictor import GenericPredictor
from Predictors.matrix_trainer import MatrixTrainer
from Predictors.deep_predictor import DeepPredictor
from Predictors.utils import Reporting
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.LogglyTracer import LogglyTracer
from tensorflow.keras.regularizers import l2

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout
from tensorflow.keras.optimizers import Adam
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.callbacks import EarlyStopping
import joblib
# endregion

type_ = "DEMO"
if type_ == "DEMO":
    live = False
else:
    live = True

# region statics
if os.name == 'nt' or os.environ.get("USER", "") == "daniel":
    account_type = "DEMO"
    conf_reader = ConfigReader(False)
    _tracer = ConsoleTracer()
else:
    conf_reader = EnvReader()
    account_type = conf_reader.get("Type")
    _tracer = LogglyTracer(conf_reader.get("loggly_api_key"), type_, "train_job")

dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx, type_)
cache = DropBoxCache(ds)
client = pymongo.MongoClient(
    f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ms = MarketStore(db)
predictor_store = PredictorStore(db)
an = Analytics(market_store=ms, ig=IG(conf_reader=conf_reader))
_trainer = MatrixTrainer(analytics=an,
                         cache=cache,
                         check_trainable=False,
                         predictor_store=predictor_store)
_tiingo = Tiingo(conf_reader=conf_reader, cache=cache, tracer=_tracer)
_dp = DataProcessor()
_trade_type = TradeType.FX
_indicators = Indicators()
_reporting = Reporting(predictor_store=predictor_store)


# endregion


def train_and_save_model(df, model_path='trading_model.h5'):
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
    model.save(model_path)
    print(f"Accurace {val_accuracy}")
    return model

def train_and_save_model_random(df, model_path='trading_model.h5') -> (RandomForestClassifier, float):
    # Spalten "Profit" muss die Zielvariable sein

    df = df.drop('chart_index', axis=1)
    X = df.drop(columns=['result'])  # Features: Alle Spalten außer 'Profit'
    y = df['result']  # Zielvariable: Spalte 'Profit'

    # Splitte die Daten in Trainings- und Testdaten (80% Training, 20% Test)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Hyperparameter-Raster
    param_grid = {
        'n_estimators': [50, 100, 200],  # Anzahl der Bäume im Wald
        'max_depth': [None, 10, 20, 30],  # Maximale Tiefe der Bäume
        'min_samples_split': [2, 5, 10, 15, 20],  # Mindestanzahl von Samples, um einen Knoten zu splitten
        'min_samples_leaf': [1, 2, 4, 8, 12],  # Mindestanzahl von Samples in einem Blatt
        'max_features': ['auto', 'sqrt'],  # Anzahl der Merkmale, die beim Splitten berücksichtigt werden
        'bootstrap': [True, False],  # Ob Bootstrap-Sampling verwendet werden soll
        'criterion': ['gini', 'entropy'],  # Split-Kriterium
        'class_weight': ['balanced', 'balanced_subsample', None],  # Gewichtung der Klassen
        'min_impurity_decrease': [0.0, 0.01, 0.1, 0.2],  # Mindestv. der Impurität für einen Split
        'max_leaf_nodes': [None, 10, 20, 50, 100],  # Maximale Anzahl an Blättern
    }


    # Modell und RandomizedSearchCV-Objekt erstellen
    rf = RandomForestClassifier()
    random_search = RandomizedSearchCV(estimator=rf, param_distributions=param_grid,
                                       n_iter=50, cv=5, verbose=0, n_jobs=-1)

    # Suche starten
    random_search.fit(X_train, y_train)

    # Genauigkeit des besten Modells anzeigen
    print("Best cross-validation accuracy:", random_search.best_score_)

    best_model = random_search.best_estimator_
    test_accuracy = best_model.score(X_test, y_test)
    print("Test accuracy with best parameters:", test_accuracy)

    validate_model(best_model, X_test, y_test)

    return best_model, test_accuracy


def get_train_data(tiingo: Tiingo, symbol: str, trade_type: TradeType, data_processor: DataProcessor, dropbox_cache:DropBoxCache) -> (DataFrame, DataFrame):
    hour_df = f"{symbol}_train_1hour.csv"
    minute_df = f"{symbol}_train_5minute.csv"

    if dropbox_cache.train_cache_exist(hour_df) and dropbox_cache.train_cache_exist(minute_df):
        df_train = dropbox_cache.load_train_cache(hour_df)
        eval_df_train = dropbox_cache.load_train_cache(minute_df)

        if "PIVOT" not in df_train.columns:
            from finta import TA
            pivot = TA.PIVOT(df_train)
            df_train["PIVOT"] = pivot["pivot"]
            df_train["S1"] = pivot["s1"]
            df_train["S2"] = pivot["s2"]
            df_train["R1"] = pivot["r1"]
            df_train["R2"] = pivot["r2"]

        if "PIVOT_FIB" not in df_train.columns:
            from finta import TA
            pivot = TA.PIVOT_FIB(df_train)
            df_train["PIVOT_FIB"] = pivot["pivot"]
            df_train["S1_FIB"] = pivot["s1"]
            df_train["S2_FIB"] = pivot["s2"]
            df_train["R1_FIB"] = pivot["r1"]
            df_train["R2_FIB"] = pivot["r2"]
    else:
        df_train, eval_df_train = tiingo.load_test_data(symbol, data_processor, trade_type=trade_type)
        dropbox_cache.save_train_cache(df_train,hour_df)
        dropbox_cache.save_train_cache(eval_df_train,minute_df)

    df_train = df_train.astype({col: 'float32' for col in df_train.select_dtypes(include='float64').columns})
    eval_df_train = eval_df_train.astype({col: 'float32' for col in eval_df_train.select_dtypes(include='float64').columns})
    return df_train, eval_df_train


def get_test_data(tiingo: Tiingo, symbol: str, trade_type: TradeType, data_processor: DataProcessor,  dropbox_cache:DropBoxCache) -> (DataFrame, DataFrame):
    hour_df = f"{symbol}_test_1hour.csv"
    minute_df = f"{symbol}_test_5minute.csv"

    if dropbox_cache.train_cache_exist(hour_df) and dropbox_cache.train_cache_exist(minute_df):
        df_train = dropbox_cache.load_train_cache(hour_df)
        eval_df_train = dropbox_cache.load_train_cache(minute_df)

        if "PIVOT" not in df_train.columns:
            from finta import TA
            pivot = TA.PIVOT(df_train)
            df_train["PIVOT"] = pivot["pivot"]
            df_train["S1"] = pivot["s1"]
            df_train["S2"] = pivot["s2"]
            df_train["R1"] = pivot["r1"]
            df_train["R2"] = pivot["r2"]

        if "PIVOT_FIB" not in df_train.columns:
            from finta import TA
            pivot = TA.PIVOT_FIB(df_train)
            df_train["PIVOT_FIB"] = pivot["pivot"]
            df_train["S1_FIB"] = pivot["s1"]
            df_train["S2_FIB"] = pivot["s2"]
            df_train["R1_FIB"] = pivot["r1"]
            df_train["R2_FIB"] = pivot["r2"]


    else:
        df_train, eval_df_train = tiingo.load_test_data(symbol, data_processor, trade_type=trade_type)
        dropbox_cache.save_train_cache(df_train, hour_df)
        dropbox_cache.save_train_cache(eval_df_train, minute_df)

    df_train = df_train.astype({col: 'float32' for col in df_train.select_dtypes(include='float64').columns})
    eval_df_train = eval_df_train.astype(
        {col: 'float32' for col in eval_df_train.select_dtypes(include='float64').columns})
    return df_train, eval_df_train

def preprocess_data(df):
    df = df.replace({'none': 0, 'both': 1, 'buy': 1, 'sell':0})
    return df

def feature_importance(merged_df):
    X = merged_df.drop(columns=["chart_index", "result"])
    y = merged_df['result']

    # Random Forest Modell
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)

    # Feature Importance
    feature_importances = pd.Series(model.feature_importances_, index=X.columns)
    feature_importances = feature_importances.sort_values(ascending=False)

    # Visualisierung der Feature-Wichtigkeiten
    #plt.figure(figsize=(12, 6))
    #sns.barplot(x=feature_importances, y=feature_importances.index)
    #plt.title("Feature-Importance basierend auf Random Forest")
    #plt.xlabel("Feature-Importance Score")
    #plt.show()

    bad_features = feature_importances[feature_importances < 0.01]
    print("bad Features", bad_features.index.tolist())

    return bad_features.index.tolist()

def validate_model(model, X, y):
    predictions = model.predict(X)
    predictions_binary = (predictions > 0.5).astype(int)  # Schwellenwert 0.5
    train_df_new = X.copy()


    train_df_new['predicted_profit'] = predictions_binary
    train_df_new['result'] = y
    train_df_new = train_df_new[train_df_new['predicted_profit'] == 1]
    accuracy = (train_df_new['predicted_profit'] == train_df_new['result']).mean()
    print(f"++++++++++++++++++++++Genauigkeit: {accuracy * 100:.2f}%")



def train_predictors(markets: list,
                     trainer: MatrixTrainer,
                     tiingo: Tiingo,
                     data_processor: DataProcessor,
                     predictor: Type,
                     indicators: Indicators,
                     reporting: Reporting,
                     trade_type: TradeType = TradeType.FX,
                     tracer=ConsoleTracer()
                     ):

    for m in random.choices(markets, k=10):
        symbol = m["symbol"]
        #if symbol != "AUDCHF":
        #    continue

        tracer.info(f"Train {symbol}")
        df_train, eval_df_train = get_train_data(tiingo, symbol, trade_type, data_processor=data_processor, dropbox_cache=cache)

        indicators.reset_caches()

        if len(df_train) == 0:
            continue

        try:
            #General
            config = predictor_store.load_active_by_symbol(symbol)
            buy_results, sell_results = trainer.simulate(df_train, eval_df_train, symbol, m["scaling"], config, epic=m["epic"])
            trainer.get_signals(symbol, df_train, indicators, GenericPredictor)
            train_signals_df = trainer.create_combined_indicator_data(indicators, symbol)

            #Buy
            print("Buy")
            train_signals_df_buy = train_signals_df.replace({'none': -0.5, 'both': 1, 'buy': 1, 'sell':-1})

            buy_results = buy_results[['chart_index', 'result']]
            buy_results['result'] = buy_results['result'].apply(lambda x: 1 if x > 0 else 0)
            signal_result_df = pd.merge(train_signals_df_buy, buy_results, on='chart_index', how='left')
            signal_result_df['result'].fillna(0, inplace=True)
            signal_result_df = signal_result_df.dropna()

            model, accuracy = train_and_save_model_random(signal_result_df)

            deep_predictor = DeepPredictor(symbol=symbol, cache=cache, config=config, tracer=tracer, indicators=indicators)
            deep_predictor.set_model_buy(model)
            deep_predictor.set_buy_validation(accuracy)

            # Sell
            print("Sell")
            train_signals_df_sell = train_signals_df.replace({'none': -0.5, 'both': 1, 'buy': -1, 'sell': 1})

            sell_results = sell_results[['chart_index', 'result']]
            sell_results['result'] = sell_results['result'].apply(lambda x: 1 if x > 0 else 0)
            signal_result_df = pd.merge(train_signals_df_sell, sell_results, on='chart_index', how='left')
            signal_result_df['result'].fillna(0, inplace=True)
            signal_result_df = signal_result_df.dropna()

            model, accuracy = train_and_save_model_random(signal_result_df)

            deep_predictor = DeepPredictor(symbol=symbol, cache=cache, config=config, tracer=tracer, indicators=indicators)
            deep_predictor.set_model_sell(model)
            deep_predictor.set_sell_validation(accuracy)



            deep_predictor.save()
            deep_predictor.activate()
            predictor_store.save(deep_predictor)





        except Exception as ex:
            traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
            print(f"MainException: {ex} File:{traceback_str}")



while True:
    try:
        train_predictors(markets=IG.get_markets_offline(),
                         trainer=_trainer,
                         tiingo=_tiingo,
                         predictor=GenericPredictor,
                         data_processor=_dp,
                         indicators=_indicators,
                         tracer=_tracer,
                         reporting=_reporting)
    except Exception as ex:
        traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
        print(f"MainException: {ex} File:{traceback_str}")
