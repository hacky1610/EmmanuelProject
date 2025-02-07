# region import
import os
import random
import traceback
from datetime import datetime
from sklearn.utils import shuffle
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
    hour_df = f"{symbol}_train_1hour_5.csv"
    minute_df = f"{symbol}_train_5minute_5.csv"

    if dropbox_cache.train_cache_exist(hour_df) and dropbox_cache.train_cache_exist(minute_df):
        df_train = dropbox_cache.load_train_cache(hour_df)
        eval_df_train = dropbox_cache.load_train_cache(minute_df)
    else:
        df_train, eval_df_train = tiingo.load_test_data(symbol, data_processor, trade_type=trade_type, use_cache=True)
        dropbox_cache.save_train_cache(df_train, hour_df)
        dropbox_cache.save_train_cache(eval_df_train, minute_df)

    df_train = df_train.astype({col: 'float32' for col in df_train.select_dtypes(include='float64').columns})
    eval_df_train = eval_df_train.astype(
        {col: 'float32' for col in eval_df_train.select_dtypes(include='float64').columns})
    return df_train, eval_df_train



def create_data(tiingo, symbol, trade_type,data_processor, trainer, hours, factor, indicators, trade_mode, cache):
    df_train, eval_df_train = get_train_data(tiingo, symbol, trade_type, data_processor=data_processor,
                                             dropbox_cache=cache)
    buy_results, sell_results = trainer.simulate(df_train, eval_df_train, symbol,
                                                 time_frame=hours, factor=factor)
    trainer.get_signals(symbol, df_train, indicators, GenericPredictor)
    train_signals_df = trainer.create_combined_indicator_data(indicators, symbol)

    # Set specific replacement values for each trade type
    if trade_mode == "buy":
        train_signals_df = train_signals_df.replace({'none': 0, 'both': 1, 'buy': 1, 'sell': 0})
        trade_results = buy_results
    elif trade_mode == "sell":
        train_signals_df = train_signals_df.replace({'none': 0, 'both': 1, 'buy': 0, 'sell': 1})
        trade_results = sell_results

    train_signals_df = train_signals_df.infer_objects(copy=False)

    # Prepare results data
    trade_results = trade_results[['chart_index', 'result']]
    trade_results['result'] = trade_results['result'].apply(lambda x: 1 if x > 0 else 0)
    signal_result_df = pd.merge(train_signals_df, trade_results, on='chart_index', how='left')
    signal_result_df['result'].fillna(0, inplace=True)
    signal_result_df = signal_result_df.dropna()

    df = signal_result_df.drop(columns=["chart_index"])
    # Split dataset into training and test sets
    df_train = df[:int(len(df) * 0.95)]
    df_test = df[int(len(df) * 0.95):]

    return df_train, df_test


def train_symbols(markets, trainer, tiingo, deep_trainer, data_processor, indicators, trade_type=TradeType.FX,
                  tracer=ConsoleTracer()):



    indicators.reset_caches()


    try:
        # General configuration and data processing
        best_buy_results = []
        best_sell_results = []

        for hours in [6,7]:
            for factor in [0.3,0.5]:
                for combination_size in [3]:
                    for quantile in [0.7,0.9]:
                        for mix in [False]:
                            iteration = 100
                            evaluate_type = "prec"
                            for use_importance in [True, False]:
                                try:
                                    print(f"Train for {hours} hours and factor {factor}")

                                    df_train_global = pd.DataFrame()
                                    df_test_global = pd.DataFrame()

                                    #for fx in ["EURCHF", "EURGBP", "USDCHF", "EURUSD", "USDJPY"]:
                                    for fx in ["EURCHF"]:
                                        df_train,df_test = create_data(tiingo, fx, trade_type, data_processor, trainer, hours, factor, indicators, "buy", cache)
                                        # Zusammenfügen der Daten
                                        df_train_global = pd.concat([df_train_global, df_train], ignore_index=True)
                                        df_test_global = pd.concat([df_test_global, df_test], ignore_index=True)

                                    if mix:
                                        df_train_global = shuffle(df_train_global, random_state=42)
                                    best_buy_results = best_buy_results + deep_trainer.train(df_train_global, df_test_global, hours, quantile,
                                                                                             iteration, evaluate_type,combination_size, use_importance)

                                    for fx in ["EURCHF"]:
                                        df_train, df_test = create_data(tiingo, fx, trade_type, data_processor, trainer,
                                                                        hours, factor, indicators, "sell", cache)
                                        # Zusammenfügen der Daten
                                        df_train_global = pd.concat([df_train_global, df_train], ignore_index=True)
                                        df_test_global = pd.concat([df_test_global, df_test], ignore_index=True)
                                    if mix:
                                        df_train_global = shuffle(df_train_global, random_state=42)
                                    best_sell_results = best_sell_results + deep_trainer.train(df_train_global, df_test_global, hours, quantile,
                                                                                             iteration, evaluate_type,combination_size,use_importance)

                                    for r in best_buy_results:
                                        r.update({"factor": factor, "combination_size":combination_size, "mix":mix , "use_importance":use_importance})

                                    for r in best_sell_results:
                                        r.update({"factor": factor, "combination_size": combination_size,"mix":mix,"use_importance":use_importance  })

                                except Exception as ex:
                                    traceback_str = traceback.format_exc()
                                    print(f"MainException: {ex} File:{traceback_str}")

        # Save and activate predictor
        # Initialize deep predictor
        config = predictor_store.load_active_by_symbol("EURUSD")

        deep_predictor = DeepPredictor(symbol="foo", cache=cache, config=config, tracer=tracer,
                                       indicators=indicators)
        global_buy_results_path = "D:\\Code\\EmmanuelCache\\global_best_buy_results.csv"
        global_sell_results_path = "D:\\Code\\EmmanuelCache\\global_best_sell_results.csv"

        if best_buy_results:

            best_buy_results_df = DataFrame(best_buy_results)
            best_buy_results_df["Symbol"] = "foo"
            best_buy_results_df = best_buy_results_df.sort_values(by="Best Reward", ascending=False)

            # Speichern der neuen individuellen CSV
            best_buy_results_df.drop(columns=["Best Model"]).to_csv(
                f"D:\\Code\\EmmanuelCache\\foo_best_buy_results_{datetime.now().microsecond}.csv", sep=';',
                index=False)

            # Hinzufügen der Daten zur globalen CSV-Datei
            if os.path.exists(global_buy_results_path):
                best_buy_results_df.drop(columns=["Best Model"]).to_csv(
                    global_buy_results_path, sep=';', index=False, header=False, mode='a')
            else:
                best_buy_results_df.drop(columns=["Best Model"]).to_csv(
                    global_buy_results_path, sep=';', index=False, header=True, mode='w')

            best_buy_precision_row = best_buy_results_df.loc[best_buy_results_df["Score"].idxmax()]
            deep_predictor.set_buy_validation(best_buy_precision_row["Best Precision"],
                                              best_buy_precision_row["Trading Houres"],
                                              threshold=best_buy_precision_row["Best Threshold"],
                                              features=best_buy_precision_row["Good Features"])
            deep_predictor.set_model_buy(best_buy_precision_row["Best Model"])


        if best_sell_results:
            best_sell_results_df = DataFrame(best_sell_results)

            best_sell_results_df["Symbol"] = "Foo"
            best_sell_results_df = best_sell_results_df.sort_values(by="Best Reward", ascending=False)

            # Speichern der neuen individuellen CSV
            best_sell_results_df.drop(columns=["Best Model"]).to_csv(
                f"D:\\Code\\EmmanuelCache\\foo_best_sell_results_{datetime.now().microsecond}.csv", sep=';',
                index=False)

            # Hinzufügen der Daten zur globalen CSV-Datei
            if os.path.exists(global_sell_results_path):
                best_sell_results_df.drop(columns=["Best Model"]).to_csv(
                    global_sell_results_path, sep=';', index=False, header=False, mode='a')
            else:
                best_sell_results_df.drop(columns=["Best Model"]).to_csv(
                    global_sell_results_path, sep=';', index=False, header=True, mode='w')
            best_sell_precision_row = best_sell_results_df.loc[best_sell_results_df["Score"].idxmax()]




            deep_predictor.set_sell_validation(best_sell_precision_row["Best Precision"],
                                               best_sell_precision_row["Trading Houres"],
                                               threshold=best_sell_precision_row["Best Threshold"],
                                               features=best_sell_precision_row["Good Features"], )
            deep_predictor.set_model_sell(best_sell_precision_row["Best Model"])

        if best_buy_results or best_sell_results:
            deep_predictor.save()
            deep_predictor.activate()
            predictor_store.save(deep_predictor)

    except Exception as ex:
        traceback_str = traceback.format_exc()
        print(f"MainException: {ex} File:{traceback_str}")


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
