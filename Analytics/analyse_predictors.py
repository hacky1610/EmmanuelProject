import pandas as pd
from Analytics.analyze_bl import AnalyzeParamCreator, Analyzer

df = pd.read_parquet("/home/daniel/Documents/Projects/predictor_5.parquet" )

creator = AnalyzeParamCreator()
analyzer = Analyzer()


best_result = analyzer.find_best_filter_combination(df)
best_df = best_result["filtered_df"]
filtered_df_without_wilson = best_df[best_df.wilson_score > 0.35]

analyzer.analyze(filtered_df_without_wilson)
filtered_df_without_wilson.to_parquet("/home/daniel/Documents/Projects/predictor_filtered.parquet")






