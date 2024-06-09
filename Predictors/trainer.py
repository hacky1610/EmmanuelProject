import itertools
import random
from datetime import datetime
from time import time
from typing import List

from pandas import DataFrame

from BL.analytics import Analytics
from BL.eval_result import EvalResult, EvalResultCollection
from BL.indicators import Indicator, Indicators
from Connectors.predictore_store import PredictorStore
from Predictors.utils import FileSystem
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.Tracer import Tracer


class Trainer:

    def __init__(self, analytics:Analytics, cache, predictor_store: PredictorStore, check_trainable=False,
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

    def train(self, symbol: str, scaling: int, df: DataFrame, df_eval: DataFrame, df_test: DataFrame,
              df_eval_test: DataFrame, predictor_class, indicators, best_indicators: List):
        self._tracer.info(
            f"#####Train {symbol} with {predictor_class.__name__} over {self._get_time_range(df)} days #######################")
        best_win_loss = 0
        best_reward = 0
        best_avg_reward = 0
        best_predictor = None
        best_config = {}

        for training_set in self._get_sets(predictor_class, best_indicators):
            predictor = predictor_class(symbol=symbol, indicators=indicators)
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

                self._tracer.info(f"{symbol} - Result {best_train_result} - Indicators {predictor._indicator_names} "
                                  f"Limit: {predictor._limit} Stop: {predictor._stop}")

        if best_predictor is not None:
            test_result: EvalResult = best_predictor.eval(df_test, df_eval_test, self._analytics, symbol, scaling)
            self._predictor_store.save(best_predictor, overwrite=False)

            self._tracer.info(
                f"Test:  WL: {test_result.get_win_loss()} - Reward: {test_result.get_reward()} Avg Reward {test_result.get_average_reward()}")
            self._tracer.info(
                f"Train: WL: {best_win_loss}           - Reward: {best_reward}       Avg Reward {best_avg_reward}")
            self._tracer.info(
                f"Stop: {best_predictor._stop} - Limit: {best_predictor._limit}   Max nones: {best_predictor._max_nones}")
        else:
            self._tracer.info("No Best predictor")

    def train_all_indicators(self, symbol: str, scaling: int, df: DataFrame, df_eval: DataFrame, df_test: DataFrame,
                             df_eval_test: DataFrame, predictor_class, indicators):
        self._tracer.info(
            f"#####Train {symbol} with {predictor_class.__name__} over {self._get_time_range(df)} days #######################")

        for indicator in indicators.get_all_indicator_names():
            self.train_indicator(indicator, symbol, scaling, df, df_eval, predictor_class, indicators)

    def train_indicator(self, indicator:str ,symbol: str, scaling: int, df: DataFrame, df_eval: DataFrame, predictor_class, indicators):
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

    def get_signals(self,symbol:str ,df: DataFrame, indicators:Indicators, predictor_class):
        for indicator in indicators.get_all_indicator_names():
            predictor = predictor_class(symbol=symbol, indicators=indicators)
            predictor.setup({"_indicator_names": [indicator], "_stop": 50, "_limit": 50})
            trades = predictor.get_signals(df, self._analytics)
            trades.to_csv(f"D:\\tmp\\signal_{symbol}_{indicator}.csv")

    def simulate(self,df: DataFrame, df_eval: DataFrame, symbol:str, scaling:int):
        res = self._analytics.simulate("buy", 50, 50, df, df_eval, symbol, scaling)
        res.to_csv(f"D:\\tmp\\simulation_buy{symbol}.csv")
        res = self._analytics.simulate("sell", 50, 50, df, df_eval, symbol, scaling)
        res.to_csv(f"D:\\tmp\\simulation_sell{symbol}.csv")




    def find_best_combination(self, symbol:str):
        import pandas as pd
        directory = "D:\Code\EmmanuelProject\Data\TrainResults"
        dfs_file_names = FileSystem.find_files_with_prefix(directory,f"trade_results_{symbol}")

        dfs = [pd.read_csv(f"{directory}\\{df}") for df in dfs_file_names]

        self._find_best_indicators(dfs, 3)

    def _find_best_indicators(self, results:List[DataFrame], combo_count:int = 4):
        all_combos = list(itertools.combinations(results, combo_count))
        best_result = -1
        best_indicators = []
        for c in all_combos:
            result = EvalResultCollection.calc_combination(list(c))
            indicator_names = EvalResultCollection.get_indicator_names(list(c))
            self._tracer.info(f"Result {result} for {indicator_names}")

            if result > best_result:
                best_indicators = indicator_names
                best_result = result

        self._tracer.info(f"Ultimate Best Result {best_result} for {best_indicators}")

    def _get_sets(self, predictor_class, best_indicators: List):
        sets = predictor_class.get_training_sets(best_indicators)
        #sets = random.choices(sets, k=5)
        random.shuffle(sets)
        sets.insert(0, {})  # insert a fake set. So that the current best version is beeing testet
        return sets
