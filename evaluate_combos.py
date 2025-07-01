# region import
import os
import random
import traceback
from typing import List, Counter

import dropbox
import pymongo
import pandas as pd
from pandas import DataFrame

import Data.combos
from BL.Simulation import Simulation
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
from Predictors.generic_predictor import GenericPredictor
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
    f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster1.uo3fjln.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ms = MarketStore(db)
predictor_store = PredictorStore(db)
an = Analytics(market_store=ms, ig=IG(conf_reader=conf_reader))
_simulation = Simulation(_cache, an)
_tiingo = Tiingo(conf_reader=conf_reader, cache=_cache, tracer=_tracer)
_dp = DataProcessor()
_trade_type = TradeType.FX
_indicators = Indicators()
_reporting = Reporting(predictor_store=predictor_store)


# endregion

low_spread_pairs = [
    "EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCHF", "NZDUSD",
    "EURJPY", "EURGBP", "USDCAD", "GBPJPY", "AUDJPY", "EURCHF",
    "EURAUD", "GBPCHF", "EURCAD", "GBPAUD", "CHFJPY", "CADJPY",
    "NZDJPY", "GBPNZD",
    "USDHKD", "USDSGD", "EURSGD", "AUDNZD", "CADCHF", "NZDCAD",
    "EURNZD", "AUDCAD", "NOKSEK", "USDNOK"
]

def create_new_combos(original_list, replacement_values):
    new_list = []

    for item in original_list:
        position = random.randint(0, len(item) - 1)  # Zufällige Position wählen
        for replacement in random.choices(replacement_values, k=25):
            new_item = item.copy()  # Kopie machen, damit Original nicht verändert wird
            new_item[position] = replacement
            new_list.append(new_item)

    return new_list

import pandas as pd

def remove_duplicates_with_unordered_list_column(df, subset, list_column):
    """
    Entfernt doppelte Zeilen aus einem DataFrame basierend auf bestimmten Spalten,
    wobei eine der Spalten eine Liste oder ein Array ist, deren Reihenfolge ignoriert wird.
    """
    if list_column not in subset:
        raise ValueError(f"Die Spalte '{list_column}' muss in der subset-Liste enthalten sein.")

    sorted_column = f'__sorted_{list_column}'
    df = df.copy()

    def normalize_to_tuple(x):
        try:
            return tuple(sorted(list(x)))
        except Exception:
            return x  # Wenn z.B. x ein einfacher String oder None ist

    df[sorted_column] = df[list_column].apply(normalize_to_tuple)

    subset_modified = [sorted_column if col == list_column else col for col in subset]

    df_cleaned = df.drop_duplicates(subset=subset_modified)
    df_cleaned = df_cleaned.drop(columns=[sorted_column])

    return df_cleaned


def get_all_combos(filter_symbol, df) -> List[str]:
    # Filtere alle Zeilen, bei denen _symbol ungleich filter_symbol ist
    filtered_df = df[df["_symbol"] != filter_symbol]

    # Extrahiere _features, aber nur wenn es sich um eine Liste handelt
    combo_list = [
        features for features in filtered_df["_features"]

    ]

    return combo_list


def get_most_used_features(df: pd.DataFrame, top_factor: float = 0.5) -> List[str]:
    features_list = []

    # Durchlaufe alle Zeilen und sammle die Features
    for features in df["_features"]:
        features_list.extend(features)

    # Zähle die Häufigkeit jedes Features
    feature_counts = Counter(features_list)

    # Anzahl der häufigsten Features, die zurückgegeben werden sollen
    top_n = int(len(feature_counts) * top_factor)

    # Liste der am häufigsten vorkommenden Features
    top_features_list = [feature for feature, _ in feature_counts.most_common(top_n)]

    return top_features_list

def analyze_by_symbol(df):
    required_columns = [
        '_symbol', '_train_precision', '_train_reward', '_test_precision',
        '_test_reward', '_test_trade_count', '_atr_factor_stop', '_atr_factor_limit'
    ]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in DataFrame: {missing}")

    grouped = df.groupby('_symbol')

    summary = grouped.agg({
        '_train_precision': ['mean', 'median'],
        '_train_reward': ['mean', 'median'],
        '_test_precision': ['mean', 'median'],
        '_test_reward': ['mean', 'median'],
        '_test_trade_count': ['sum'],
    })

    # Spaltennamen flach machen
    summary.columns = ['_'.join(col).strip() for col in summary.columns.values]
    summary = summary.rename(columns={'_symbol_count': 'num_entries'})

    return summary

def train_symbols(markets, simulation, cache, tiingo, data_processor, indicators, trade_type=TradeType.FX,
                  tracer=ConsoleTracer()):
    # General configuration and data processing
    markets = IG.get_markets_offline()
    random.shuffle(markets)
    for market in markets:

        fx = market["symbol"]


        #ct._save_predictor(fx,"",6, ["rsi_border","bb_border_limit", "adx", "macd_turn"],1,1,10,1.2,0.8,1,1,10,100)
        #continue


        if fx not in low_spread_pairs:
            continue

        #fx = "EURNZD"
        indicators.reset_caches()

        #if predictor_store.count_of_all_by_symbol(fx) > 40:
        #    print("Enough training data to train")
        #    continue

        df = pd.read_parquet("predictors.parquet")
        online_combos = get_all_combos(fx,df)
        online_combos = online_combos + create_new_combos(online_combos, indicators.get_all_indicator_names())

        best_features_online_0_5 = get_most_used_features(df, 0.33)
        best_features_online_0_2 = get_most_used_features(df,0.15)

        hours = 16
        data = random.choice([(2.0,2.1,0.8, 0.7,6),
                              (2.0,2.7,0.8, 0.7,6),
                              (2.0, 2.1, 0.9, 0.7, 6),
                              (2.0, 2.7, 0.9, 0.7, 6),
                              (1.5, 2.0, 0.9, 0.7, 6),
                              (1.2, 1.8, 0.9, 0.7, 6)
                     ])
        atr_factor_stop = data[0]
        atr_factor_limit = data[1]
        minimum_precission_train = data[2]
        minimum_precission_test = data[3]
        min_train_reward=data[4]

        combis = [(4, 0.1),
                  (5, 0.1),
                  (6, 0.1),
                  (8, 0.1),
                  (7, 0.2)]

        for combination_size_tuple in random.choices(combis,k=3):

            f = 0
            combination_size = combination_size_tuple[0]
            part = combination_size_tuple[1]
            for features in [
                             random.choices( indicators.get_all_indicator_names(), k=25)]:
                f += 1

                ct = CombinationTrainer(cache=cache,
                                        indicators=indicators,
                                        predictor_store=predictor_store,
                                        test_mode=True)
                try:

                    for trade_action in [TradeAction.SELL,TradeAction.BUY]:
                        print(
                            f"Evaluate {fx} {trade_action} for {hours} hours and stop factor "
                            f"{atr_factor_stop} limit {atr_factor_limit} and min prec {minimum_precission_train} combination {combination_size} Feature Set {f}")
                        df_train_global = ct.create_data(tiingo=tiingo, symbol=fx,
                                                         trade_type=trade_type, data_processor=data_processor,
                                                         simulation=simulation, hours=hours,
                                                         factor_stop=atr_factor_stop, factor_limit=atr_factor_limit,
                                                         indicators=indicators,
                                                         trade_mode=trade_action, cache=cache)

                        train_df = ct.train(df=df_train_global,
                                 trading_hours=hours,
                                 min_prec_train=minimum_precission_train,
                                 num_features=combination_size,
                                 trading_mode=trade_action,
                                 symbol=fx,
                                 atr_factor_stop=atr_factor_stop,
                                 atr_factor_limit=atr_factor_limit,
                                 best_features=features, min_prec_test=minimum_precission_test,
                                 part=part,existing_combos=[],
                                 min_train_reward=min_train_reward)

                        if len(train_df) > 0:
                            train_df["_symbol"] = fx
                            train_df["_atr_factor_stop"] = atr_factor_stop
                            train_df["_atr_factor_limit"] = atr_factor_limit
                            all_df = pd.read_parquet('predictor_2.parquet')
                            all_df = pd.concat([all_df,train_df],  ignore_index=True)
                            all_df = remove_duplicates_with_unordered_list_column(all_df,["_symbol", "_atr_factor_stop", "_atr_factor_limit", "_features"], "_features")
                            all_df.to_parquet('predictor_2.parquet')
                            print("")




                except Exception as ex:
                    traceback_str = traceback.format_exc()
                    print(f"MainException: {ex} File:{traceback_str}")


while True:
    try:
        train_symbols(markets=IG.get_markets_offline(),
                      tiingo=_tiingo,
                      data_processor=_dp,
                      indicators=_indicators,
                      tracer=_tracer,
                      cache=_cache,
                      simulation=_simulation)
        print("")
    except Exception as ex:
        traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
        print(f"MainException: {ex} File:{traceback_str}")
