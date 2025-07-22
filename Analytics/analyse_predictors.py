import os

import pandas as pd
from Analytics.analyze_bl import AnalyzeParamCreator, Analyzer


def is_clustered(row, min_variance=80, min_span=200, max_density=0.1):
    indexes = row['_train_indexes']
    if indexes is None or len(indexes) < 2:
        return True

    span = max(indexes) - min(indexes)
    density = row['_train_trade_count'] / span if span > 0 else float('inf')

    return row['_train_variance'] < min_variance or span < min_span or density > max_density

pd.set_option('display.max_columns', None)

if os.name == "nt":
    df = pd.read_parquet("C:\\Users\\adhada7\\Projects\predictor_win_5.parquet")
else:
    df = pd.read_parquet("/home/daniel/Documents/Projects/predictor_5.parquet")

creator = AnalyzeParamCreator()
analyzer = Analyzer()

df_with_params = creator.add_measure_parameters(df)


#print("Analyze Original DF")
#analyzer.analyze(df_with_params)


print("Analyze Filtered DF")

#filtered_df = df_with_params[
#    (df_with_params['cluster_size_median'] <= 2) &
#    (df_with_params['max_cluster_size'] <= 4) &
#    (df_with_params['outlier_count'] <= 1) &
#    (df_with_params['_test_trade_count'] >= 5) &
#    (df_with_params['features_len'] <= 6)
#]

best_result = analyzer.find_best_filter_combination(df_with_params)
best_df = best_result["filtered_df"]
filtered_df_without_wilson = best_df[best_df.wilson_score > 0.35]


analyzer.analyze(filtered_df_without_wilson)






