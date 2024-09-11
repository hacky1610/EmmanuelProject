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
        best_train_result = EvalResult()
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

            train_result = predictor.train(df_train=df, df_eval=df_eval, analytics=self._analytics, symbol=symbol,
                                           scaling=scaling)
            if train_result is None:
                return

            if best_train_result.is_better(train_result) and train_result.get_trades() > 70:
                best_predictor = predictor
                best_train_result = train_result
                best_config = predictor.get_config()

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
                    f"Train: WL: {best_train_result.get_win_loss():.2f} - Reward: {best_predictor.get_result().get_reward():.2f} Avg Reward {best_predictor.get_result().get_average_reward():.2f}")
                self._tracer.info(f"{best_predictor} ")
            else:
                self._tracer.info("No good predictor")
        else:
            self._tracer.info("No Best predictor")

    def _get_sets(self, predictor_class, best_indicators: List, best_indicator_combos: List[List[str]]):
        sets = predictor_class.get_training_sets(best_indicator_combos)
        #sets = random.choices(sets, k=5)
        random.shuffle(sets)
        sets.insert(0, {})  # insert a fake set. So that the current best version is beeing testet
        return sets
