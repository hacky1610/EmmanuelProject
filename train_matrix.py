# region import
import os
import random
import traceback
from itertools import combinations
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
ps = PredictorStore(db)
an = Analytics(market_store=ms, ig=IG(conf_reader=conf_reader))
_trainer = MatrixTrainer(analytics=an,
                   cache=cache,
                   check_trainable=False,
                   predictor_store=ps)
_tiingo = Tiingo(conf_reader=conf_reader, cache=cache, tracer=_tracer)
_dp = DataProcessor()
_trade_type = TradeType.FX
_indicators = Indicators()
_reporting = Reporting(predictor_store=ps)


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
    early_stopping = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)

    # Modell trainieren
    history = model.fit(X_train, y_train, validation_data=(X_test, y_test), epochs=100, batch_size=32,
                        callbacks=[early_stopping], verbose=0)

    # Zugriff auf val_loss und val_accuracy
    val_loss = history.history['val_loss'][-1]
    val_accuracy = history.history['val_accuracy'][-1]

    # Modell speichern
    model.save(model_path)
    print(f"Accurace {val_accuracy}")
    return model

def get_train_data(tiingo: Tiingo, symbol: str, trade_type: TradeType, dp: DataProcessor, dropbox_cache:DropBoxCache) -> (DataFrame, DataFrame):
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
        df_train, eval_df_train = tiingo.load_train_data(symbol, dp, trade_type=trade_type)
        dropbox_cache.save_train_cache(df_train,hour_df)
        dropbox_cache.save_train_cache(eval_df_train,minute_df)

    df_train = df_train.astype({col: 'float32' for col in df_train.select_dtypes(include='float64').columns})
    eval_df_train = eval_df_train.astype({col: 'float32' for col in eval_df_train.select_dtypes(include='float64').columns})
    return df_train, eval_df_train


def get_test_data(tiingo: Tiingo, symbol: str, trade_type: TradeType, dp: DataProcessor,  dropbox_cache:DropBoxCache) -> (DataFrame, DataFrame):
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
        df_train, eval_df_train = tiingo.load_test_data(symbol, dp, trade_type=trade_type)
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
    plt.figure(figsize=(12, 6))
    sns.barplot(x=feature_importances, y=feature_importances.index)
    plt.title("Feature-Importance basierend auf Random Forest")
    plt.xlabel("Feature-Importance Score")
   #plt.show()

    bad_features = feature_importances[feature_importances < 0.01]
    print("bad Features", bad_features.index.tolist())

    return bad_features.index.tolist()




def train_predictors(markets: list,
                     trainer: MatrixTrainer,
                     tiingo: Tiingo,
                     dp: DataProcessor,
                     predictor: Type,
                     indicators: Indicators,
                     reporting: Reporting,
                     trade_type: TradeType = TradeType.FX,
                     tracer=ConsoleTracer()
                     ):

    for m in random.choices(markets, k=10):
        symbol = m["symbol"]
        #if symbol != "EURGBP":
        #    continue

        tracer.info(f"Train {symbol}")
        df_train, eval_df_train = get_train_data(tiingo, symbol, trade_type, dp,dropbox_cache=cache)
        df_test, eval_df_test = get_test_data(tiingo, symbol, trade_type, dp, dropbox_cache=cache)

        indicators.reset_caches()

        if len(df_train) == 0:
            continue

        _reporting.create(markets, predictor)

        try:
            config = ps.load_active_by_symbol(symbol)
            buy_results, sell_results = trainer.simulate(df_train, eval_df_train, symbol, m["scaling"], config, epic=m["epic"])
            buy_results_test, sell_results_test = trainer.simulate_test(df_test, eval_df_test, symbol, m["scaling"], config,
                                                         epic=m["epic"])
            trainer.get_signals(symbol, df_test, indicators, predictor)
            trainer.get_signals_test(symbol, df_test, indicators, predictor)

            df = trainer.create_combined_indicator_data(indicators, symbol)

            df = df.replace({'none': 0, 'both': 1, 'buy': 1, 'sell':0})



            buy_results = buy_results[['chart_index', 'result']]
            buy_results['result'] = buy_results['result'].apply(lambda x: 1 if x > 0 else 0)
            merged_df = pd.merge(df, buy_results, on='chart_index', how='left')
            merged_df['result'].fillna(0, inplace=True)
            merged_df = merged_df.dropna()

            #Feature

            bad_features = feature_importance(merged_df)

            # Fülle eventuelle fehlende Werte in der `result`-Spalte mit 0 oder einem gewünschten Wert

            model = train_and_save_model(merged_df)

            train_and_save_model(merged_df.drop(columns=bad_features))
            continue

            df_test = trainer.create_combined_indicator_data_test(indicators, symbol)
            df_test = df_test.replace({'none': 0, 'both': 1, 'buy': 1, 'sell': 0})
            buy_results_test = buy_results_test[['chart_index', 'result']]
            buy_results_test['result'] = buy_results_test['result'].apply(lambda x: 1 if x > 0 else 0)
            merged_df_test = pd.merge(df_test, buy_results_test, on='chart_index', how='left')
            merged_df_test['result'].fillna(0, inplace=True)
            merged_df_test = merged_df_test.dropna()

            predictions = model.predict(merged_df_test.drop(columns=['result', 'chart_index']))
            predictions_binary = (predictions > 0.5).astype(int)  # Schwellenwert 0.5



            merged_df_test['predicted_profit'] = predictions_binary
            accuracy = (merged_df_test['predicted_profit'] == merged_df_test['result']).mean()
            print(f"Genauigkeit: {accuracy * 100:.2f}%")

            # Optional: Die ersten Zeilen ausgeben, um die Ergebnisse zu überprüfen
            print(merged_df_test[['profit', 'predicted_profit']].head())

        except Exception as ex:
            traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
            print(f"MainException: {ex} File:{traceback_str}")



while True:
    try:
        train_predictors(markets=IG.get_markets_offline(),
                         trainer=_trainer,
                         tiingo=_tiingo,
                         predictor=GenericPredictor,
                         dp=_dp,
                         indicators=_indicators,
                         tracer=_tracer,
                         reporting=_reporting)
    except Exception as ex:
        traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
        print(f"MainException: {ex} File:{traceback_str}")
