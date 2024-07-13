import itertools
import os.path
import random
import traceback
from datetime import datetime
from typing import List

import pandas as pd
from pandas import DataFrame
from tqdm import tqdm

from BL.analytics import Analytics
from BL.eval_result import EvalResult, EvalResultCollection
from BL.indicators import Indicators
from BL import measure_time
from BL.eval_result import EvalResult
from Connectors.predictore_store import PredictorStore
from Predictors.utils import FileSystem
from Predictors.base_predictor import BasePredictor
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.Tracer import Tracer


class Trainer:

    def __init__(self, analytics: Analytics, cache, predictor_store: PredictorStore, check_trainable=False,
                 tracer: Tracer = ConsoleTracer()):
        self._analytics = analytics
        self._cache = cache
        self._check_trainable = check_trainable
        self._tracer = tracer
        self._predictor_store = predictor_store

    def is_trained(self,
                   symbol: str,
                   version: str,
                   predictor) -> bool:
        saved_predictor = predictor(cache=self._cache).load(symbol)
        return version == saved_predictor.version

    def _trainable(self, predictor):
        if not self._check_trainable:
            return True

        if predictor.get_result().get_trades() < 8:
            print("To less trades")
            return False
        if predictor.get_result().get_win_loss() < 0.67:
            print("To less win losses")
            return False
        return True

    def _get_time_range(self, df):
        return (datetime.now() - datetime.strptime(df.iloc[0].date, "%Y-%m-%dT%H:%M:%S.%fZ")).days

    @measure_time
    def train(self, symbol: str, scaling: int, df: DataFrame, df_eval: DataFrame,
              df_test: DataFrame, df_eval_test: DataFrame, predictor_class,
              indicators, best_indicators: List, best_online_config: dict, best_indicator_combos: List[List[str]]):
        self._tracer.info(
            f"#####Train {symbol} with {predictor_class.__name__} over {self._get_time_range(df)} days #######################")
        best_win_loss = 0
        best_reward = 0
        best_avg_reward = 0
        best_predictor = None
        best_config = {}

        training_sets = self._get_sets(predictor_class, best_indicators, best_indicator_combos)
        training_sets.insert(0, best_online_config)

        for training_set in tqdm(training_sets):
            predictor: BasePredictor = predictor_class(symbol=symbol, indicators=indicators)
            predictor.setup(self._predictor_store.load_active_by_symbol(symbol))
            predictor.setup(best_config)
            if not self._trainable(predictor):
                self._tracer.info("Predictor is not trainable")
                return
            predictor.setup(training_set)

            best_train_result = predictor.train(df_train=df, df_eval=df_eval, analytics=self._analytics, symbol=symbol,
                                                scaling=scaling)
            if best_train_result is None:
                return

            if best_train_result.get_reward() > best_reward and best_train_result.get_win_loss() >= 0.66 and best_train_result.get_trades() >= 15:
                best_reward = best_train_result.get_reward()
                best_win_loss = best_train_result.get_win_loss()
                best_avg_reward = best_train_result.get_average_reward()
                best_predictor = predictor
                best_config = predictor.get_config()

                #self._tracer.info(f"{symbol} - Result {best_train_result} - Indicators {predictor._indicator_names} "
                #                  f"{predictor} ")

        if best_predictor is not None:
            self._tracer.info(
                f"#####Test {symbol}  over {self._get_time_range(df_test)} days #######################")
            test_result: EvalResult = best_predictor.eval(df_test, df_eval_test, self._analytics, symbol, scaling)
            if best_predictor.get_result().get_reward() > 0:
                best_predictor.activate()
                self._predictor_store.save(best_predictor, overwrite=False)

                self._tracer.info(
                    f"Test:  WL: {test_result.get_win_loss():.2f} - Reward: {test_result.get_reward():.2f} Avg Reward {test_result.get_average_reward():.2f}")
                self._tracer.info(
                    f"Train: WL: {best_win_loss:.2f} - Reward: {best_reward:.2f} Avg Reward {best_avg_reward:.2f}")
                self._tracer.info(f"{best_predictor} ")
            else:
                self._tracer.info("No good predictor")
        else:
            self._tracer.info("No Best predictor")

    def train_all_indicators(self, symbol: str, scaling: int, df: DataFrame, df_eval: DataFrame, df_test: DataFrame,
                             df_eval_test: DataFrame, predictor_class, indicators):
        self._tracer.info(
            f"#####Train {symbol} with {predictor_class.__name__} over {self._get_time_range(df)} days #######################")

        for indicator in indicators.get_all_indicator_names():
            self.train_indicator(indicator, symbol, scaling, df, df_eval, predictor_class, indicators)

    def train_indicator(self, indicator: str, symbol: str, scaling: int, df: DataFrame, df_eval: DataFrame,
                        predictor_class, indicators):
        self._tracer.info(f"Train Indicator {indicator}")
        if EvalResult.is_trained(symbol, indicator):
            self._tracer.info(f"Indicator {indicator} already trained")
            return

        predictor = predictor_class(symbol=symbol, indicators=indicators)
        predictor.setup({"_indicator_names": [indicator], "_stop": 54, "_limit": 51.2})

        best_train_result = predictor.train(df_train=df, df_eval=df_eval, analytics=self._analytics, symbol=symbol,
                                            scaling=scaling, only_one_position=False)
        if best_train_result is not None:
            best_train_result.save_trade_result()

    def get_signals(self, symbol: str, df: DataFrame, indicators: Indicators, predictor_class):
        for indicator in indicators.get_all_indicator_names():
            path = f"D:\\tmp\\Signals\\signal_{symbol}_{indicator}.csv"
            if not os.path.exists(path):
                predictor = predictor_class(symbol=symbol, indicators=indicators)
                predictor.setup({"_indicator_names": [indicator], "_stop": 50, "_limit": 50})
                trades = predictor.get_signals(df, self._analytics)
                trades.to_csv(path)

    @measure_time
    def simulate(self, df: DataFrame, df_eval: DataFrame, symbol: str, scaling: int, current_config: dict):
        buy_path = f"D:\\tmp\\Simulations\\simulation_buy{symbol}{current_config['_stop']}{current_config['_limit']}{current_config['_use_isl']}{current_config['_isl_distance']}{current_config['_isl_open_end']}.csv"
        sell_path = f"D:\\tmp\\Simulations\\simulation_sell{symbol}{current_config['_stop']}{current_config['_limit']}{current_config['_use_isl']}{current_config['_isl_distance']}{current_config['_isl_open_end']}.csv"

        if not os.path.exists(buy_path):
            buy = self._analytics.simulate(action="buy", stop_euro=current_config["_stop"],
                                           isl_entry=current_config.get("_isl_entry", 0),
                                           isl_distance=current_config.get("_isl_distance", 0),
                                           isl_open_end=current_config.get("_isl_open_end", False),
                                           use_isl=current_config.get("_use_isl", False),
                                           limit_euro=current_config["_limit"], df=df, df_eval=df_eval,
                                           symbol=symbol, scaling=scaling)
            if buy is not None:
                buy.to_csv(buy_path)
        else:
            buy = pd.read_csv(buy_path)
        if not os.path.exists(sell_path):
            sell = self._analytics.simulate(action="sell", stop_euro=current_config["_stop"],
                                            isl_entry=current_config.get("_isl_entry", 0),
                                            isl_distance=current_config.get("_isl_distance", 0),
                                            isl_open_end=current_config.get("_isl_open_end", False),
                                            use_isl=current_config.get("_use_isl", False),
                                            limit_euro=current_config["_limit"], df=df, df_eval=df_eval,
                                            symbol=symbol, scaling=scaling)
            if sell is not None:
                sell.to_csv(sell_path)
        else:
            sell = pd.read_csv(sell_path)
        return buy, sell

    @measure_time
    def foo_combinations(self, symbol: str, indicators: Indicators, best_combo_list: List[List[str]],
                         current_indicators: List[str], buy_results, sell_results):
        df_list = []
        current_indicators_objects = []
        current_indicators_combos = []
        for indicator in indicators.get_all_indicator_names():
            try:
                indicator_object = {"indicator": indicator,
                                    "data": pd.read_csv(f"D:\\tmp\\Signals\\signal_{symbol}_{indicator}.csv")}
                df_list.append(indicator_object)
                if indicator in current_indicators:
                    current_indicators_objects.append(indicator_object)
            except Exception as e:
                print(f"Error {e}")
                pass

        all_combos = list(itertools.combinations(df_list, random.randint(4, 5)))

        for i in df_list:
            new_list = current_indicators_objects.copy()
            new_list.append(i)
            current_indicators_combos.append(new_list)

            new_list = current_indicators_objects.copy()
            new_list.pop(random.randint(0, len(current_indicators_objects) - 1))
            new_list.append(i)
            current_indicators_combos.append(new_list)

        if len(df_list) != len(indicators.get_all_indicator_names()):
            print("Not all indicators are there")

        best_combo_object_list = []
        for combo in best_combo_list:
            combo_objects = []
            for indicator in df_list:
                if indicator["indicator"] in combo:
                    combo_objects.append(indicator)
            best_combo_object_list.append(combo_objects)

        best_result = -10000
        best_combo = []
        filtered_combos = random.choices(all_combos, k=2000)
        all_combos = best_combo_object_list + filtered_combos
        for combo in tqdm(all_combos):
            signals = EvalResultCollection.calc_combination([item['data'] for item in combo])
            current_result = self._analytics.foo(signals, buy_results, sell_results)
            if current_result > best_result:
                best_result = current_result
                best_combo = [item['indicator'] for item in combo]

        return best_combo

    @measure_time
    def foo_combinations2(self, symbol: str, indicators: Indicators, best_combo_online: List[str],
                          current_indicators: List[str], buy_results, sell_results):

        merge_path = f"D:\\tmp\\Merged\\{symbol}.csv"
        if not os.path.exists(merge_path):
            merged = self.merge_signal_simmulations(indicators, buy_results, sell_results, symbol)
            merged.to_csv(merge_path)
        else:
            merged = pd.read_csv(merge_path)

        all_combos = list(itertools.combinations(indicators.get_all_indicator_names(), random.randint(4, 5)))
        filtered_combos = random.choices(all_combos, k=4000)
        filtered_combos.insert(0, best_combo_online)

        def filter_rows(row):
            return (row >= 0).all() or (row <= 0).all()

        best_combo = None
        best_sum = -100000
        for combo in tqdm(filtered_combos):
            combo = list(combo)
            filtered_df = merged[combo]
            filtered_df.dropna(inplace=True)
            filtered_df = filtered_df[filtered_df.apply(filter_rows, axis=1)]

            filtered_df['Result'] = filtered_df.sum(axis=1)
            sum = filtered_df['Result'].sum()
            if sum > best_sum:
                best_combo = combo
                best_sum = sum

        return best_combo

    def merge_signal_simmulations(self, indicators, buy_results, sell_results, symbol):
        date_frames = []
        for i in tqdm(indicators.get_all_indicator_names()):
            try:

                signals = pd.read_csv(f"D:\\tmp\\Signals\\signal_{symbol}_{i}.csv")
                date_frames.append(self._analytics.simulate_signal(signals, buy_results, sell_results, i))

            except Exception as e:
                traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
                print(f"MainException: {e} File:{traceback_str}")
        merged_df = date_frames[0]
        # Schleife durch die restlichen DataFrames und mergen
        for df in date_frames[1:]:
            merged_df = pd.merge(merged_df, df, on="chart_index", how="outer")
        return merged_df

    def find_best_combination(self, symbol: str):
        import pandas as pd
        directory = "D:\Code\EmmanuelProject\Data\TrainResults"
        dfs_file_names = FileSystem.find_files_with_prefix(directory, f"trade_results_{symbol}")

        dfs = [pd.read_csv(f"{directory}\\{df}") for df in dfs_file_names]

        self._find_best_indicators(dfs, 3)

    def _find_best_indicators(self, results: List[DataFrame], combo_count: int = 4):
        all_combos = list(itertools.combinations(results, combo_count))
        best_result = -1
        for c in all_combos:
            result = EvalResultCollection.calc_combination(list(c))

    def _get_sets(self, predictor_class, best_indicators: List, best_indicator_combos: List[List[str]]):
        sets = predictor_class.get_training_sets(best_indicator_combos)
        #sets = random.choices(sets, k=5)
        random.shuffle(sets)
        sets.insert(0, {})  # insert a fake set. So that the current best version is beeing testet
        return sets
