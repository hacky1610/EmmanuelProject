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
from Connectors.dropbox_cache import DropBoxCache
from Connectors.predictore_store import PredictorStore
from Predictors.utils import FileSystem
from Predictors.base_predictor import BasePredictor
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.Tracer import Tracer


class MatrixTrainer:

    def __init__(self, analytics: Analytics, cache:DropBoxCache, predictor_store: PredictorStore, check_trainable=False,
                 tracer: Tracer = ConsoleTracer()):
        self._analytics = analytics
        self._cache = cache
        self._check_trainable = check_trainable
        self._tracer = tracer
        self._predictor_store = predictor_store

    def get_signals(self, symbol: str, df: DataFrame, indicators: Indicators, predictor_class):
        for indicator in indicators.get_all_indicator_names():
            path = f"signal_{symbol}_{indicator}.csv"
            if not self._cache.signal_exist(path):
                print(f"Create signal for {indicator}")
                predictor = predictor_class(symbol=symbol, indicators=indicators)
                predictor.setup({"_indicator_names": [indicator], "_stop": 50, "_limit": 50})
                trades = predictor.get_signals(df, self._analytics)
                self._cache.save_signal(trades, path)

    @measure_time
    def simulate(self, df: DataFrame, df_eval: DataFrame, symbol: str, scaling: int, current_config: dict):
        buy_path = f"simulation_buy{symbol}{current_config.get('_stop')}{current_config.get('_limit')}{current_config.get('_use_isl', False)}{current_config.get('_isl_distance', 20)}{current_config.get('_isl_open_end', False)}.csv"
        sell_path = f"simulation_sell{symbol}{current_config.get('_stop')}{current_config.get('_limit')}{current_config.get('_use_isl', False)}{current_config.get('_isl_distance', 20)}{current_config.get('_isl_open_end', False)}.csv"

        if not self._cache.simulation_exist(buy_path):
            buy = self._analytics.simulate(action="buy", stop_euro=current_config["_stop"],
                                           isl_entry=current_config.get("_isl_entry", 0),
                                           isl_distance=current_config.get("_isl_distance", 0),
                                           isl_open_end=current_config.get("_isl_open_end", False),
                                           use_isl=current_config.get("_use_isl", False),
                                           limit_euro=current_config["_limit"], df=df, df_eval=df_eval,
                                           symbol=symbol, scaling=scaling)
            if buy is not None:
                self._cache.save_simulation(buy,buy_path)
        else:
            buy = self._cache.load_simulation(buy_path)

        if not self._cache.simulation_exist(sell_path):
            sell = self._analytics.simulate(action="sell", stop_euro=current_config["_stop"],
                                            isl_entry=current_config.get("_isl_entry", 0),
                                            isl_distance=current_config.get("_isl_distance", 0),
                                            isl_open_end=current_config.get("_isl_open_end", False),
                                            use_isl=current_config.get("_use_isl", False),
                                            limit_euro=current_config["_limit"], df=df, df_eval=df_eval,
                                            symbol=symbol, scaling=scaling)
            if sell is not None:
                self._cache.save_simulation(sell,sell_path)
        else:
            sell = self._cache.load_simulation(sell_path)
        return buy, sell

    @measure_time
    def train_combinations(self, symbol: str, indicators: Indicators, best_combo_list: List[List[str]],
                           current_indicators: List[str], buy_results, sell_results):
        df_list = []
        current_indicators_objects = []
        current_indicators_combos = []
        for indicator in indicators.get_all_indicator_names():
            try:
                indicator_object = {"indicator": indicator,
                                    "data": self._cache.load_signal(f"signal_{symbol}_{indicator}.csv")}
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
            current_result = self._analytics.calculate_overall_result(signals, buy_results, sell_results)
            if current_result > best_result:
                print(f"New best result {current_result} from {[item['indicator'] for item in combo]}")
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

                signals = self._cache.load_signal(f"signal_{symbol}_{i}.csv")
                date_frames.append(self._analytics.simulate_signal(signals, buy_results, sell_results, i))

            except Exception as e:
                traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
                print(f"MainException: {e} File:{traceback_str}")
        merged_df = date_frames[0]
        # Schleife durch die restlichen DataFrames und mergen
        for df in date_frames[1:]:
            merged_df = pd.merge(merged_df, df, on="chart_index", how="outer")
        return merged_df

    def _find_best_indicators(self, results: List[DataFrame], combo_count: int = 4):
        all_combos = list(itertools.combinations(results, combo_count))
        best_result = -1
        for c in all_combos:
            result = EvalResultCollection.calc_combination(list(c))

