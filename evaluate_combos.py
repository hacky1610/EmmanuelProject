# region import
import os
import traceback
import dropbox
import pymongo
import pandas as pd
from pandas import DataFrame
from BL.analytics import Analytics
from BL.combination_trainer import CombinationTrainer
from BL.data_processor import DataProcessor
from BL.datatypes import TradeAction
from BL.indicators import Indicators
from BL.utils import ConfigReader, EnvReader
from Connectors.IG import IG
from Connectors.dropbox_cache import DropBoxCache
from Connectors.dropboxservice import DropBoxService
from Connectors.market_store import MarketStore
from Connectors.predictore_store import PredictorStore
from Connectors.tiingo import TradeType, Tiingo
from Predictors.deep_predictor import DeepPredictor
from Predictors.generic_predictor import GenericPredictor
from Predictors.matrix_trainer import MatrixTrainer
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
_cache = DropBoxCache(ds)
client = pymongo.MongoClient(
    f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ms = MarketStore(db)
predictor_store = PredictorStore(db)
an = Analytics(market_store=ms, ig=IG(conf_reader=conf_reader))
_trainer = MatrixTrainer(analytics=an,
                         cache=_cache,
                         check_trainable=False,
                         predictor_store=predictor_store)
_tiingo = Tiingo(conf_reader=conf_reader, cache=_cache, tracer=_tracer)
_dp = DataProcessor()
_trade_type = TradeType.FX
_indicators = Indicators()
_reporting = Reporting(predictor_store=predictor_store)


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

def _create_hash(df):
    return df.date.iloc[0] + df.date.iloc[-1]

def create_data(tiingo, symbol, trade_type,data_processor, trainer, hours, factor, indicators, trade_mode:str, cache) -> (DataFrame, DataFrame, str):
    df_train, eval_df_train = get_train_data(tiingo, symbol, trade_type, data_processor=data_processor,
                                             dropbox_cache=cache)
    hash = _create_hash(df_train )
    buy_results, sell_results = trainer.simulate(df_train, eval_df_train, symbol,
                                                 time_frame=hours, factor=factor)
    trainer.get_signals(symbol, df_train, indicators, GenericPredictor)
    train_signals_df = trainer.create_combined_indicator_data(indicators, symbol)

    # Set specific replacement values for each trade type
    if trade_mode ==  TradeAction.BUY:
        train_signals_df = train_signals_df.replace({'none': 0, 'both': 1, 'buy': 1, 'sell': 0})
        trade_results = buy_results
    elif trade_mode == TradeAction.SELL:
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

    return df, hash


def train_symbols(markets, trainer, cache, tiingo, data_processor, indicators, trade_type=TradeType.FX,
                  tracer=ConsoleTracer()):

    # General configuration and data processing
    for fx in ["EURUSD"]:
        indicators.reset_caches()

        #if predictor_store.count_of_all_by_symbol(fx) > 40:
        #    print("Enough training data to train")
        #    continue

        for hours in [16]:
            for factor in [2.0]:
                combination_size = 4
                quantile = 0.88
                ct = CombinationTrainer(cache=cache,
                                        indicators=indicators,
                                        predictor_store=predictor_store,
                                        test_mode=True)
                try:
                    print(f"Evaluate {fx}  for {hours} hours and factor {factor} and quantille {quantile} combination {combination_size}")

                    for trade_action in [TradeAction.BUY, TradeAction.SELL]:
                        df_train_global, df_hash = create_data(tiingo, fx,
                                                               trade_type, data_processor,
                                                               trainer, hours,
                                                               factor, indicators,
                                                               trade_action, cache)

                        ct.train(df=df_train_global,
                                 trading_hours=hours,
                                 min_prec=quantile,
                                 num_features=combination_size,
                                 trading_mode=trade_action,
                                 symbol=fx,
                                 atr_factor=factor)

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
                      cache= _cache)
    except Exception as ex:
        traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
        print(f"MainException: {ex} File:{traceback_str}")
