from datetime import datetime, date
from typing import Type
from collections import Counter
from pandas import DataFrame, Series
from BL.eval_result import EvalResultCollection
from BL.indicators import Indicators


class TimeUtils:

    @staticmethod
    def get_time_string(da: datetime):
        return da.strftime("%Y-%m-%dT%H:00:00.000Z")

    @staticmethod
    def get_date_string(da: date):
        return da.strftime("%Y-%m-%d")

class Reporting:

    def __init__(self, cache):
        self._cache = cache

    def report_predictor(self,symbol,  predictor_class:Type, verbose:bool):
        predictor = predictor_class(cache=self._cache, indicators=Indicators())
        predictor.load(symbol)
        if verbose:
            print(f"{symbol} - {predictor.get_last_result()} {predictor._indicator_names}")
        return predictor.get_last_result(),  Series([symbol,
                       predictor._limit_factor,
                       predictor._indicator_names,
                       predictor.get_last_result().get_win_loss(),
                       predictor.get_last_result().get_trade_frequency()],
                      index=["symbol",
                             "_limit_factor",
                             "_indicator_names",
                             "win_los",
                             "frequence"])

    def report_predictors(self,markets, predictor_class:Type, verbose:bool = True) -> (EvalResultCollection, DataFrame):
        results = EvalResultCollection()
        df = DataFrame()
        for market in markets:
            result,data = self.report_predictor(market["symbol"], predictor_class, verbose)
            results.add(result)
            df = df.append(data, ignore_index=True)

        return results, df

    def get_best_indicators(self,markets, predictor_class:Type):
        results, df = self.report_predictors(markets,predictor_class, verbose=False)

        best_df = df[df.win_los > 0.66]
        indicators = []
        for r in best_df.iterrows():
            indicators = indicators + r[1]._indicator_names
        string_counts = Counter(indicators)
        most_common_strings = string_counts.most_common()

        best_indicators = []
        for indicator, c in most_common_strings[:7]:
            best_indicators.append(indicator)

        return best_indicators
