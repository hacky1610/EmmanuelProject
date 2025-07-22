import os

import pandas
import pandas as pd
from pandas import DataFrame

from Analytics.analyze_bl import AnalyzeParamCreator, Analyzer

if os.name == "nt":
    df = pd.read_parquet("C:\\Users\\adhada7\\Projects\predictor_win_5.parquet")
else:
    df = pd.read_parquet("/home/daniel/Documents/Projects/predictor_5.parquet")

creator = AnalyzeParamCreator()
analyzer = Analyzer()


results_per_symbol = {}


best_df = DataFrame()
for symbol, df_symbol in df.groupby('_symbol'):
    best_result = analyzer.find_best_filter_combination(df_symbol)
    best_df = pd.concat([best_df, best_result["filtered_df"]], axis=0, ignore_index=True)


best_df = best_df[best_df.wilson_score > 0.35]

analyzer.analyze(best_df)
#best_df.to_parquet("/home/daniel/Documents/Projects/predictor_filtered.parquet")






