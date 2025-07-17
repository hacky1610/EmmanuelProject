# region import
import os
import random
import time
import traceback
from typing import List, Counter
from contextlib import contextmanager
import pandas as pd
import numpy as np
import multiprocessing as mp

import dropbox
import pymongo

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

def create_new_combos(original_list: List[List[str]], replacement_values: List[str], k: int = 25) -> List[List[str]]:
    """
    Erstellt neue Kombos, indem für jede originale Kombo ein zufälliges Element durch ein zufälliges Replacement ersetzt wird.
    """
    new_list = []
    for item in original_list:
        if not item:
            continue
        position = random.randint(0, len(item) - 1)
        for replacement in random.sample(replacement_values, min(k, len(replacement_values))):
            new_item = item.copy()
            new_item[position] = replacement
            new_list.append(new_item)
    return new_list

def remove_duplicates_with_unordered_list_column(df: pd.DataFrame, subset: List[str], list_column: str) -> pd.DataFrame:
    """
    Entfernt doppelte Zeilen aus einem DataFrame basierend auf bestimmten Spalten,
    wobei eine der Spalten eine Liste oder ein Array ist, deren Reihenfolge ignoriert wird.
    """
    if list_column not in subset:
        raise ValueError(f"Die Spalte '{list_column}' muss in der subset-Liste enthalten sein.")

    sorted_column = f'__sorted_{list_column}'
    df = df.copy()

    def normalize_to_tuple(x):
        if isinstance(x, (list, np.ndarray)):
            return tuple(sorted(x))
        return x

    df[sorted_column] = df[list_column].apply(normalize_to_tuple)
    subset_modified = [sorted_column if col == list_column else col for col in subset]
    df_cleaned = df.drop_duplicates(subset=subset_modified)
    df_cleaned = df_cleaned.drop(columns=[sorted_column])
    return df_cleaned

def get_all_combos(filter_symbol: str, df: pd.DataFrame) -> List[List[str]]:
    filtered_df = df[df["_symbol"] != filter_symbol]
    all_combos = (tuple(sorted(f)) for f in filtered_df["_features"] if isinstance(f, (list, np.ndarray)))
    unique_combos = [list(t) for t in set(all_combos)]
    return unique_combos

def get_most_used_features(df: pd.DataFrame, top_factor: float = 0.5) -> List[str]:
    features_list = []
    for features in df["_features"]:
        features_list.extend(features)
    feature_counts = Counter(features_list)
    top_n = max(1, int(len(feature_counts) * top_factor))
    top_features_list = [feature for feature, _ in feature_counts.most_common(top_n)]
    return top_features_list

LOCKFILE_PATH = "predictor_2.parquet.lock"

@contextmanager
def file_lock(lockfile_path, check_interval=0.5, timeout=60):
    start_time = time.time()
    while True:
        try:
            fd = os.open(lockfile_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            break
        except FileExistsError:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Timeout while waiting for lock {lockfile_path}")
            time.sleep(check_interval)
    try:
        yield
    finally:
        if os.path.exists(lockfile_path):
            os.remove(lockfile_path)

def train_symbols(markets, simulation, cache, tiingo, data_processor, indicators, trade_type=TradeType.FX,
                  tracer=ConsoleTracer()):
    markets = IG.get_markets_offline()
    random.shuffle(markets)
    parquet_name = "predictor_5.parquet"
    if os.name == "nt":
        parquet_name = "predictor_win.parquet"

    for market in markets:
        fx = market["symbol"]
        if fx not in low_spread_pairs:
            continue
        indicators.reset_caches()

        with file_lock(LOCKFILE_PATH):
            df = pd.read_parquet("predictor_4.parquet")

        online_combos = get_all_combos(fx, df)
        online_combos += create_new_combos(online_combos, indicators.get_all_indicator_names())
        random.shuffle(online_combos)
        reduced_size = min(350000, len(online_combos))
        online_combos = online_combos[:reduced_size]

        best_features_online_0_5 = get_most_used_features(df, 0.33)
        best_features_online_0_2 = get_most_used_features(df, 0.15)

        data = random.choice([
            (2.0, 2.1, 0.90, 0.7, 20),
            (2.0, 2.7, 0.90, 0.7, 20),
            (1.5, 2.0, 0.90, 0.7, 20),
            (1.2, 1.8, 0.90, 0.7, 20),
            (1.0, 1.6, 0.90, 0.7, 20),
        ])
        atr_factor_stop, atr_factor_limit, min_prec_train, min_prec_test, min_train_reward = data
        ct = CombinationTrainer(
            cache=cache,
            indicators=indicators,
            predictor_store=predictor_store,
            test_mode=True
        )

        combos = [online_combos]
        for combination_size in random.choices([4,5,6,7,8], k=3):
            combos.append(ct.create_combos(best_features_online_0_5, combination_size))
            combos.append(ct.create_combos(best_features_online_0_2, combination_size))
            combos.append(ct.create_combos(random.sample(indicators.get_all_indicator_names(), 25), combination_size))

        for combo in combos:
            for trade_action in [TradeAction.SELL, TradeAction.BUY]:
                print(
                    f"Evaluate {fx} {trade_action} and stop factor "
                    f"{atr_factor_stop} limit {atr_factor_limit} and min prec {min_prec_train} combination {len(combo)} Feature Set"
                )

                df_train_global = ct.create_data(
                    tiingo=tiingo,
                    symbol=fx,
                    trade_type=trade_type,
                    data_processor=data_processor,
                    simulation=simulation,
                    factor_stop=atr_factor_stop,
                    factor_limit=atr_factor_limit,
                    indicators=indicators,
                    trade_mode=trade_action,
                    cache=cache
                )

                train_df = ct.train(
                    df=df_train_global,
                    min_prec_train=min_prec_train,
                    atr_factor_stop=atr_factor_stop,
                    trading_mode=trade_action,
                    atr_factor_limit=atr_factor_limit,
                    combos=combo,
                    min_train_reward=min_train_reward
                )

                if len(train_df) > 0:
                    train_df["_symbol"] = fx
                    train_df["_atr_factor_stop"] = atr_factor_stop
                    train_df["_atr_factor_limit"] = atr_factor_limit

                    with file_lock(LOCKFILE_PATH):
                        all_df = pd.read_parquet(parquet_name)
                        all_df = pd.concat([all_df, train_df], ignore_index=True)
                        all_df = remove_duplicates_with_unordered_list_column(
                            all_df,
                            ["_symbol", "_atr_factor_stop", "_atr_factor_limit", "_features", "_trade_mode"],
                            "_features"
                        )
                        all_df.to_parquet(parquet_name)


if __name__ == '__main__':
    while True:
        try:
            train_symbols(
                markets=IG.get_markets_offline(),
                tiingo=_tiingo,
                data_processor=_dp,
                indicators=_indicators,
                tracer=_tracer,
                cache=_cache,
                simulation=_simulation
            )
            print("")
        except Exception as ex:
            traceback_str = traceback.format_exc()
            print(f"MainException: {ex} File:{traceback_str}")