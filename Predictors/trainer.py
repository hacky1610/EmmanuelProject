import random
from datetime import datetime
from time import time
from typing import List

from pandas import DataFrame

from BL.eval_result import EvalResult
from Connectors.predictore_store import PredictorStore
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

    def train(self, symbol: str, scaling:int, df: DataFrame, df_eval: DataFrame, df_test: DataFrame, df_eval_test: DataFrame, predictor_class, indicators, best_indicators: List):
        self._tracer.info(
            f"#####Train {symbol} with {predictor_class.__name__} over {self._get_time_range(df)} days #######################")
        best_win_loss = 0
        best_reward = 0
        best_avg_reward = 0
        best_predictor = None

        for training_set in self._get_sets(predictor_class, best_indicators):
            predictor = predictor_class(symbol=symbol, indicators=indicators)
            predictor.setup(self._predictor_store.load_active_by_symbol(symbol))
            if not self._trainable(predictor):
                self._tracer.info("Predictor is not trainable")
                return
            predictor.setup(training_set)

            res: EvalResult = predictor.train(df_train=df, df_eval=df_eval, analytics=self._analytics, symbol=symbol, scaling=scaling)
            if res is None:
                return

            if res.get_reward() > best_reward and res.get_win_loss() >= 0.66 and res.get_trades() >= 15:
                best_reward = res.get_reward()
                best_win_loss = res.get_win_loss()
                best_avg_reward = res.get_average_reward()
                best_predictor = predictor
                best_predictor.activate()
                self._predictor_store.save(best_predictor)

                self._tracer.info(f"{symbol} - Result {res} - Indicators {predictor._indicator_names} "
                                  f"Limit: {predictor._limit} Stop: {predictor._stop}")

        if best_predictor is not None:
            res_test: EvalResult = best_predictor.eval(df_test, df_eval_test, self._analytics, symbol, scaling)
            best_predictor.activate()
            self._predictor_store.save(best_predictor)

            self._tracer.info(f"Test:  WL: {res_test.get_win_loss()} - Reward: {res_test.get_reward()} Avg Reward {res_test.get_average_reward()}")
            self._tracer.info(f"Train: WL: {best_win_loss}           - Reward: {best_reward}       Avg Reward {best_avg_reward}")
            self._tracer.info(f"Stop: {best_predictor._stop} - Limit: {best_predictor._limit}   Max nones: {best_predictor._max_nones}")
        else:
            self._tracer.info("No Best predictor")


    def _get_sets(self, predictor_class , best_indicators: List):
        sets = predictor_class.get_training_sets(best_indicators)
        #sets = random.choices(sets, k=5)
        random.shuffle(sets)
        sets.insert(0, {})  # insert a fake set. So that the current best version is beeing testet
        return sets
