import random
from datetime import datetime
from time import time
from typing import List

from pandas import DataFrame

from BL.eval_result import EvalResult


class Trainer:

    def __init__(self, analytics, cache, check_trainable=False):
        self._analytics = analytics
        self._cache = cache
        self._check_trainable = check_trainable

    def is_trained(self,
                   symbol: str,
                   version: str,
                   predictor) -> bool:
        saved_predictor = predictor(cache=self._cache).load(symbol)
        return version == saved_predictor.version

    def _trainable(self, predictor):
        if not self._check_trainable:
            return True

        if predictor.get_last_result().get_trades() < 8:
            print("To less trades")
            return False
        if predictor.get_last_result().get_win_loss() < 0.67:
            print("To less win losses")
            return False
        return True

    def _get_time_range(self, df):
        return (datetime.now() - datetime.strptime(df.iloc[0].date, "%Y-%m-%dT%H:%M:%S.%fZ")).days

    def train(self, symbol: str, scaling:int, df: DataFrame, df_eval: DataFrame, df_test: DataFrame, df_eval_test: DataFrame,
              version: str, predictor_class, indicators, best_indicators: List):
        print(
            f"#####Train {symbol} with {predictor_class.__name__} over {self._get_time_range(df)} days #######################")
        best_win_loss = 0
        best_reward = 0
        best_avg_reward = 0
        best_predictor = None
        startzeit = time()

        for training_set in self._get_sets(predictor_class, version, best_indicators):
            predictor = predictor_class(indicators=indicators, cache=self._cache)
            predictor.load(symbol)
            if not self._trainable(predictor):
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
                best_predictor.save(symbol)

                print(f"{symbol} - Result {res} - Indicators {predictor._indicator_names}")

        if best_predictor is not None:
            res_test: EvalResult = best_predictor.eval(df_test, df_eval_test, self._analytics, symbol, scaling)
            best_predictor.save(symbol)

            print(f"Test:  WL: {res_test.get_win_loss()} - Reward: {res_test.get_reward()} Avg Reward {res_test.get_average_reward()}")
            print(f"Train: WL: {best_win_loss}           - Reward: {best_reward}       Avg Reward {best_avg_reward}")
            print(f"Stop: {best_predictor.stop} - Limit: {best_predictor.limit}   Max nones: {best_predictor._max_nones}")
        else:
            print("No Best predictor")

        #print(f"Needed time for {symbol} -  {(time() - startzeit) / 60} minutes")

    def _get_sets(self, predictor_class, version, best_indicators: List):
        sets = predictor_class.get_training_sets(version, best_indicators)
        #sets = random.choices(sets, k=5)
        random.shuffle(sets)
        sets.insert(0, {"version": version})  # insert a fake set. So that the current best version is beeing testet
        return sets
