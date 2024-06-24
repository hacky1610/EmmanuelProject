import random
from datetime import datetime
from time import time
from typing import List

from pandas import DataFrame
from tqdm import tqdm

from BL.eval_result import EvalResult
from Connectors.predictore_store import PredictorStore
from Predictors.base_predictor import BasePredictor
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.Tracer import Tracer


class Trainer:

    def __init__(self, analytics, cache, predictor_store: PredictorStore, check_trainable=False, tracer:Tracer = ConsoleTracer()):
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

    def train(self, symbol: str, scaling:int, df: DataFrame, df_eval: DataFrame,
              df_test: DataFrame, df_eval_test: DataFrame, predictor_class,
              indicators, best_indicators: List, best_online_config:dict):
        self._tracer.info(
            f"#####Train {symbol} with {predictor_class.__name__} over {self._get_time_range(df)} days #######################")
        best_win_loss = 0
        best_reward = 0
        best_avg_reward = 0
        best_predictor = None
        best_config = {}

        training_sets = self._get_sets(predictor_class, best_indicators)
        training_sets.insert(0, best_online_config)

        for training_set in tqdm(training_sets):
            predictor:BasePredictor = predictor_class(symbol=symbol, indicators=indicators)
            predictor.setup(self._predictor_store.load_active_by_symbol(symbol))
            predictor.setup(best_config)
            if not self._trainable(predictor):
                self._tracer.info("Predictor is not trainable")
                return
            predictor.setup(training_set)

            best_train_result = predictor.train(df_train=df, df_eval=df_eval, analytics=self._analytics, symbol=symbol, scaling=scaling)
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
            test_result: EvalResult = best_predictor.eval(df_test, df_eval_test, self._analytics, symbol, scaling)
            self._predictor_store.save(best_predictor, overwrite=False)

            self._tracer.info(f"Test:  WL: {test_result.get_win_loss():.2f} - Reward: {test_result.get_reward():.2f} Avg Reward {test_result.get_average_reward():.2f}")
            self._tracer.info(f"Train: WL: {best_win_loss:.2f} - Reward: {best_reward:.2f} Avg Reward {best_avg_reward:.2f}")
            self._tracer.info(f"{best_predictor} ")
        else:
            self._tracer.info("No Best predictor")


    def _get_sets(self, predictor_class , best_indicators: List):
        sets = predictor_class.get_training_sets(best_indicators)
        #sets = random.choices(sets, k=5)
        random.shuffle(sets)
        sets.insert(0, {})  # insert a fake set. So that the current best version is beeing testet
        return sets
