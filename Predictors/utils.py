import os
from datetime import datetime, date
from typing import Type, List, Dict
from collections import Counter
from pandas import DataFrame, Series
from BL.eval_result import EvalResultCollection
from BL.indicators import Indicators
from Connectors.predictore_store import PredictorStore


class TimeUtils:

    @staticmethod
    def get_time_string(da: datetime):
        return da.strftime("%Y-%m-%dT%H:00:00.000Z")

    @staticmethod
    def get_date_string(da: date):
        return da.strftime("%Y-%m-%d")

class FileSystem:

    @staticmethod
    def find_files_with_prefix(directory, prefix):
        matched_files = []
        for filename in os.listdir(directory):
            if filename.startswith(prefix):
                matched_files.append(filename)
        return matched_files


class Reporting:

    def __init__(self, predictor_store: PredictorStore):
        self._predictor_store = predictor_store
        self.results: EvalResultCollection = None
        self.reports: DataFrame = DataFrame()
        self._min_reward = 600

    def create(self, markets:List[Dict], predictor_class, verbose=False):
        self.results, self.reports = self.report_predictors(markets, predictor_class, verbose)

    def report_predictor(self, symbol: str, predictor_class: Type, verbose: bool):
        predictor = predictor_class(symbol=symbol, indicators=Indicators())
        predictor.setup(self._predictor_store.load_active_by_symbol(symbol))
        if verbose:
            print(f"{symbol} - {predictor.get_result()} {predictor._indicator_names}")
        return predictor.get_result(), Series([symbol,
                                               predictor._indicator_names,
                                               predictor.get_result().get_win_loss(),
                                               predictor.get_result().get_trades(),
                                               predictor.get_result().get_trade_frequency(),
                                               predictor.get_result().get_reward()],
                                              index=["symbol",
                                                     "_indicator_names",
                                                     "win_los",
                                                     "trades",
                                                     "frequence",
                                                     "reward"])

    def report_predictors(self, markets:List[Dict], predictor_class: Type, verbose: bool = True) -> (
    EvalResultCollection, DataFrame):
        results = EvalResultCollection()
        df = DataFrame()
        for market in markets:
            result, data = self.report_predictor(market["symbol"], predictor_class, verbose)
            results.add(result)
            df = df.append(data, ignore_index=True)

        df.fillna(0, inplace=True)
        return results, df

    def get_best_indicators_by_reward(self):

        best_df = self.reports.sort_values(by='reward', ascending=False)[:int(len(self.reports)/3)]
        indicators = []
        for r in best_df.iterrows():
            indicators = indicators + r[1]._indicator_names
        string_counts = Counter(indicators)

        return string_counts

    def get_best_indicators(self):

        best_df = self.reports[self.reports.win_los > 0.8]
        best_df = best_df[best_df.trades > 50]
        indicators = []
        for r in best_df.iterrows():
            indicators = indicators + r[1]._indicator_names
        string_counts = Counter(indicators)

        return string_counts

    def get_best_indicator_names_by_reward(self) -> List[str]:

        best_df = self.reports.sort_values(by='reward', ascending=False)[:int(len(self.reports) / 3)]
        indicators = []
        for r in best_df.iterrows():
            indicators = indicators + r[1]._indicator_names

        return list(set(indicators))

    def get_best_indicator_names(self) -> List[str]:

        best_df = self.reports[self.reports.win_los > 0.8]
        best_df = best_df[best_df.trades > 50]
        indicators = []
        for r in best_df.iterrows():
            indicators = indicators + r[1]._indicator_names

        return list(set(indicators))

    def get_best_indicator_combos_by_reward(self) -> List[List[str]]:

        best_df = self.reports.sort_values(by='reward', ascending=False)[:int(len(self.reports)/3)]
        return best_df['_indicator_names'].tolist()

    def get_best_indicator_combos(self) -> List[List[str]]:

        best_df = self.reports[self.reports.win_los > 0.8]
        best_df = best_df[best_df.trades > 50]
        return best_df['_indicator_names'].tolist()

    def get_all_indicators(self):
        indicators = []
        for r in self.reports.iterrows():
            indicators = indicators + r[1]._indicator_names

        string_counts = Counter(indicators)
        #most_common_strings = string_counts.most_common()

        return string_counts
