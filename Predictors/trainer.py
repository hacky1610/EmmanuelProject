import random
from datetime import datetime
from time import time

from BL.eval_result import EvalResult


class Trainer:

    def __init__(self, analytics, cache, check_trainable = False):
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

    def train(self, symbol: str, df, df_eval, version: str, predictor_class, indicators):
        print(f"#####Train {symbol} with {predictor_class.__name__} over {self._get_time_range(df)} days #######################")
        best_win_loss = 0
        best_predictor = None
        predictor = None
        startzeit = time()

        for training_set in self._get_sets(predictor_class, version):
            predictor = predictor_class(indicators=indicators, cache=self._cache)
            predictor.load(symbol)
            if not self._trainable(predictor):
                return
            predictor.setup(training_set)

            res: EvalResult = predictor.step(df, df_eval, self._analytics)

            if res.get_win_loss() >= best_win_loss and res.get_trades() >= 15:
                best_win_loss = res.get_win_loss()
                best_predictor = predictor
                best_predictor.save(symbol)
                print(f"{symbol} - Result {res}")

        if best_predictor is not None:
            print(f"{symbol} Overwrite result.")
            best_predictor.save(symbol)
        else:
            print(f"{symbol} Couldnt find good result")
            predictor.save(symbol)

        print(f"Needed time for {symbol} -  {(time() - startzeit) / 60} minutes")

    def _get_sets(self, predictor_class, version):
        sets = predictor_class.get_training_sets(version)
        sets = random.choices(sets, k=7)
        random.shuffle(sets)
        sets.insert(0, {"version": version})  # insert a fake set. So that the current best version is beeing testet
        return sets
