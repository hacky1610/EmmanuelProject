# region import
import os
import random
import traceback
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

def get_train_data(tiingo: Tiingo, symbol: str, trade_type: TradeType, data_processor: DataProcessor, dropbox_cache:DropBoxCache) -> (DataFrame, DataFrame):
    hour_df = f"{symbol}_train_1hour.csv"
    minute_df = f"{symbol}_train_5minute.csv"

    if dropbox_cache.train_cache_exist(hour_df) and dropbox_cache.train_cache_exist(minute_df):
        df_train = dropbox_cache.load_train_cache(hour_df)
        eval_df_train = dropbox_cache.load_train_cache(minute_df)
    else:
        df_train, eval_df_train = tiingo.load_test_data(symbol, data_processor, trade_type=trade_type)
        dropbox_cache.save_train_cache(df_train,hour_df)
        dropbox_cache.save_train_cache(eval_df_train,minute_df)

    df_train = df_train.astype({col: 'float32' for col in df_train.select_dtypes(include='float64').columns})
    eval_df_train = eval_df_train.astype({col: 'float32' for col in eval_df_train.select_dtypes(include='float64').columns})
    return df_train, eval_df_train


def train_for_trade_type(symbol, train_signals_df, trade_results, deep_trainer, deep_predictor, trade_mode):
    print(f"Train {symbol} for {trade_mode}")
    # Set specific replacement values for each trade type
    if trade_mode == "buy":
        train_signals_df = train_signals_df.replace({'none': -0.5, 'both': 1, 'buy': 1, 'sell': -1})
    elif trade_mode == "sell":
        train_signals_df = train_signals_df.replace({'none': -0.5, 'both': 1, 'buy': -1, 'sell': 1})

    train_signals_df = train_signals_df.infer_objects(copy=False)

    # Prepare results data
    trade_results = trade_results[['chart_index', 'result']]
    trade_results['result'] = trade_results['result'].apply(lambda x: 1 if x > 0 else 0)
    signal_result_df = pd.merge(train_signals_df, trade_results, on='chart_index', how='left')
    signal_result_df['result'].fillna(0, inplace=True)
    signal_result_df = signal_result_df.dropna()

    # Train model and set predictor
    model, accuracy = deep_trainer.train(signal_result_df)
    if trade_mode == "buy":
        deep_predictor.set_model_buy(model)
        deep_predictor.set_buy_validation(accuracy)
    elif trade_mode == "sell":
        deep_predictor.set_model_sell(model)
        deep_predictor.set_sell_validation(accuracy)


def train_symbols(markets, trainer, tiingo, deep_trainer, data_processor, indicators, trade_type=TradeType.FX,
                  tracer=ConsoleTracer()):
    for m in random.choices(markets, k=10):
        symbol = m["symbol"]


        if symbol != "AUDUSD":
            continue
        tracer.info(f"Train {symbol}")
        df_train, eval_df_train = get_train_data(tiingo, symbol, trade_type, data_processor=data_processor,
                                                 dropbox_cache=cache)

        indicators.reset_caches()
        if len(df_train) == 0:
            continue

        try:
            # General configuration and data processing
            config = predictor_store.load_active_by_symbol(symbol)
            buy_results, sell_results = trainer.simulate(df_train, eval_df_train, symbol, m["scaling"], config,
                                                         epic=m["epic"])
            trainer.get_signals(symbol, df_train, indicators, GenericPredictor)
            train_signals_df = trainer.create_combined_indicator_data(indicators, symbol)

            # Initialize deep predictor
            deep_predictor = DeepPredictor(symbol=symbol, cache=cache, config=config, tracer=tracer,
                                           indicators=indicators)

            # Train for Buy and Sell separately
            train_for_trade_type(symbol, train_signals_df, buy_results, deep_trainer, deep_predictor, trade_mode="buy")
            train_for_trade_type(symbol, train_signals_df, sell_results, deep_trainer, deep_predictor,
                                 trade_mode="sell")

            # Save and activate predictor
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
