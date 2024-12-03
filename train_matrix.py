# region import
import os
import random
import traceback
from datetime import datetime

import dropbox
import pymongo
import pandas as pd
from pandas import DataFrame
from BL.analytics import Analytics
from BL.data_processor import DataProcessor
from BL.deep_trainer import DeepTrainer
from BL.indicators import Indicators
from BL.utils import ConfigReader, EnvReader
from Connectors.IG import IG
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
_deep_trainer = DeepTrainer()


# endregion

def get_train_data(tiingo: Tiingo, symbol: str, trade_type: TradeType, data_processor: DataProcessor,
                   dropbox_cache: DropBoxCache) -> (DataFrame, DataFrame):
    hour_df = f"{symbol}_train_1hour.csv"
    minute_df = f"{symbol}_train_5minute.csv"

    if dropbox_cache.train_cache_exist(hour_df) and dropbox_cache.train_cache_exist(minute_df):
        df_train = dropbox_cache.load_train_cache(hour_df)
        eval_df_train = dropbox_cache.load_train_cache(minute_df)
    else:
        df_train, eval_df_train = tiingo.load_test_data(symbol, data_processor, trade_type=trade_type)
        dropbox_cache.save_train_cache(df_train, hour_df)
        dropbox_cache.save_train_cache(eval_df_train, minute_df)

    df_train = df_train.astype({col: 'float32' for col in df_train.select_dtypes(include='float64').columns})
    eval_df_train = eval_df_train.astype(
        {col: 'float32' for col in eval_df_train.select_dtypes(include='float64').columns})
    return df_train, eval_df_train


def train_for_trade_type(symbol, train_signals_df, trade_results, deep_trainer, trade_mode, hours, quantile,iterations, evaluate_type,min_feature_factor):
    print(f"Train {symbol} for {trade_mode}")
    # Set specific replacement values for each trade type
    if trade_mode == "buy":
        train_signals_df = train_signals_df.replace({'none': 0.2, 'both': 1, 'buy': 1, 'sell': 0})
    elif trade_mode == "sell":
        train_signals_df = train_signals_df.replace({'none': 0.2, 'both': 1, 'buy': 0, 'sell': 1})

    train_signals_df = train_signals_df.infer_objects(copy=False)

    # Prepare results data
    trade_results = trade_results[['chart_index', 'result']]
    trade_results['result'] = trade_results['result'].apply(lambda x: 1 if x > 0 else 0)
    signal_result_df = pd.merge(train_signals_df, trade_results, on='chart_index', how='left')
    signal_result_df['result'].fillna(0, inplace=True)
    signal_result_df = signal_result_df.dropna()

    # Train model and set predictor
    return deep_trainer.train(signal_result_df, hours, quantile,iterations, evaluate_type,min_feature_factor)


def train_symbols(markets, trainer, tiingo, deep_trainer, data_processor, indicators, trade_type=TradeType.FX,
                  tracer=ConsoleTracer()):
    for m in random.choices(markets, k=10):
        symbol = m["symbol"]

        #if symbol != "NZDCAD":
        #    continue
        tracer.info(f"Train {symbol}")
        df_train, eval_df_train = get_train_data(tiingo, symbol, trade_type, data_processor=data_processor,
                                                 dropbox_cache=cache)

        indicators.reset_caches()
        if len(df_train) == 0:
            continue

        try:
            # General configuration and data processing
            config = predictor_store.load_active_by_symbol(symbol)
            best_buy_results = []
            best_sell_results = []
            for hours in range(2, 7):
                for quantile in [0.33,0.66]:
                    iteration = 110
                    evaluate_type = "prec"
                    for min_feature_factor in [0.5]:
                        print(f"Train {symbol} for {hours} hours and quantile {quantile}")
                        buy_results, sell_results = trainer.simulate(df_train, eval_df_train, symbol,
                                                                     time_frame=hours)
                        trainer.get_signals(symbol, df_train, indicators, GenericPredictor)
                        train_signals_df = trainer.create_combined_indicator_data(indicators, symbol)

                        # Train for Buy and Sell separately
                        best_buy_results = best_buy_results + train_for_trade_type(symbol, train_signals_df, buy_results,
                                                                                   deep_trainer, trade_mode="buy",
                                                                                   hours=hours, quantile=quantile,iterations=iteration, evaluate_type=evaluate_type, min_feature_factor=min_feature_factor)
                        best_sell_results = best_sell_results + train_for_trade_type(symbol, train_signals_df, sell_results,
                                                                                     deep_trainer,
                                                                                     trade_mode="sell", hours=hours,
                                                                                     quantile=quantile,iterations=iteration, evaluate_type=evaluate_type, min_feature_factor=min_feature_factor)

            best_buy_results_df = pd.DataFrame(best_buy_results)
            best_sell_results_df = pd.DataFrame(best_sell_results)

            # Speichern der Ergebnisse
            save_to_csv(best_buy_results_df, symbol, "best_buy_results")
            save_to_csv(best_sell_results_df, symbol, "best_sell_results")

            # Beste Precision-Row für Kauf und Verkauf ermitteln
            best_buy_precision_row = get_best_precision_row(best_buy_results_df)
            best_sell_precision_row = get_best_precision_row(best_sell_results_df)


            print(f"Best Buy: {best_buy_precision_row}")
            print(f"Best Sell: {best_sell_precision_row}")

            # DeepPredictor konfigurieren
            deep_predictor = DeepPredictor(symbol=symbol, cache=cache, config=config, tracer=tracer,
                                           indicators=indicators)
            configure_deep_predictor(deep_predictor, best_buy_precision_row, best_sell_precision_row)

            # DeepPredictor speichern
            predictor_store.save(deep_predictor)

        except Exception as ex:
            traceback_str = traceback.format_exc()
            print(f"MainException: {ex} File:{traceback_str}")

    # Funktion, um das DataFrame zu speichern
def save_to_csv(df, symbol, file_suffix):
    # Bestimme das Basisverzeichnis basierend auf dem Betriebssystem
    if os.name == "nt":  # Windows
        base_dir = "D:\\Code\\EmmanuelCache"
    else:  # Linux oder andere Unix-basierte Systeme
        base_dir = os.path.expanduser("~/Code/EmmanuelCache")

    # Stelle sicher, dass das Verzeichnis existiert
    os.makedirs(base_dir, exist_ok=True)

    # Erstelle den Dateipfad
    file_name = os.path.join(base_dir, f"{symbol}_{file_suffix}_{datetime.now().microsecond}.csv")

    # Speichere den DataFrame
    df.drop(columns=["Best Model", "Feature Factors"]).to_csv(file_name, sep=';', index=False)

# Funktion, um das beste Precision-Row für Kauf und Verkauf zu finden
def get_best_precision_row(df, score_column="Train Full Reward", filter_column="CV Score",
                           threshold=0.72):
    filtered_df = df[df[filter_column] >= threshold]
    if len(filtered_df) == 0:
        return None
    filtered_df = filtered_df[filtered_df["Train Full Precision"] > 0.88]
    if len(filtered_df) == 0:
        return None
    return filtered_df.loc[filtered_df[score_column].idxmax()]

def configure_deep_predictor(deep_predictor:DeepPredictor, best_buy_row, best_sell_row):
    if best_buy_row is not None:
        deep_predictor.set_buy_validation(
            accuracy=best_buy_row["CV Score Full"],
            trading_hours=best_buy_row["Trading Houres"],
            threshold=best_buy_row["Train Full Threshold"],
            feature_factors=best_buy_row["Feature Factors"]
        )
        deep_predictor.set_model_buy(best_buy_row["Best Model"])

    if best_sell_row is not None:
        deep_predictor.set_sell_validation(
            accuracy=best_sell_row["CV Score Full"],
            trading_hours=best_sell_row["Trading Houres"],
            threshold=best_sell_row["Train Full Threshold"],
            feature_factors=best_sell_row["Feature Factors"]
        )
        deep_predictor.set_model_sell(best_sell_row["Best Model"])

    if best_sell_row is not None or best_buy_row is not None:
        deep_predictor.save()
        deep_predictor.activate()

while True:
    try:
        train_symbols(markets=IG.get_markets_offline(),
                      trainer=_trainer,
                      tiingo=_tiingo,
                      data_processor=_dp,
                      indicators=_indicators,
                      tracer=_tracer,
                      deep_trainer=_deep_trainer)
    except Exception as ex:
        traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
        print(f"MainException: {ex} File:{traceback_str}")
