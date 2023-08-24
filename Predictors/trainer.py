import random
from BL.eval_result import EvalResult


class Trainer:

    def __init__(self, analytics, cache):
        self._analytics = analytics
        self._cache = cache

    def is_trained(self,
                   symbol: str,
                   version: str,
                   predictor) -> bool:
        saved_predictor = predictor(cache=self._cache).load(symbol)
        return version == saved_predictor.version

    def train(self, symbol: str, df, df_eval, version: str, predictor_class):
        print(f"#####Train {symbol} with {predictor_class.__name__} #######################")
        best = 0
        best_predictor = None
        predictor = None

        sets = predictor_class.get_training_sets(version)
        random.shuffle(sets)
        sets.insert(0, {"version": version})  # insert a fake set. So that the current best version is beeing testet
        for training_set in sets:
            predictor = predictor_class(cache=self._cache)
            predictor.load(symbol)
            if predictor.get_last_result().get_trades() < 8:
                print(f"{symbol} To less trades")
                return
            if predictor.get_last_result().get_win_loss() < 0.67:
                print(f"{symbol} To less win losses")
                return
            predictor.setup(training_set)

            res: EvalResult = predictor.step(df, df_eval, self._analytics)

            if res.get_reward() > best and res.get_win_loss() > 0.6 and res.get_trades() >= 2:
                best = res.get_reward()
                best_predictor = predictor
                best_predictor.save(symbol)
                print(f"{symbol} - {predictor.get_config()} - Result {res}")

        if best_predictor is not None:
            print(f"{symbol} Overwrite result.")
            best_predictor.save(symbol)
        else:
            print(f"{symbol} Couldnt find good result")
            predictor.save(symbol)
