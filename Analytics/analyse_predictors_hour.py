import os

import dropbox
import pandas
import pandas as pd
from pandas import DataFrame

from Analytics.analyze_bl import AnalyzeParamCreator, Analyzer
from BL import ConfigReader
from Connectors.dropbox_cache import DropBoxCache
from Connectors.dropboxservice import DropBoxService


train_parquet_name = "C:\\Users\\adhada7\\Projects\predictor_win_7_hour.parquet"
live_parquet_name = "C:\\Users\\adhada7\\Projects\predictor_filtered_hour.parquet"


df = pd.read_parquet(train_parquet_name)
conf_reader = ConfigReader(live_config=False)
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx, "DEMO")
cache = DropBoxCache(ds)
creator = AnalyzeParamCreator()
analyzer = Analyzer()
#df = creator.add_measure_parameters(df)


results_per_symbol = {}
df = df[df._test_reward > 8]
df = df[df.cluster_count > 4]
df = df[df._test_precision > 0.8]
analyzer.analyze(df)
exit(0)
#df = df[df._train_precision > 0.8]
#df = df[df.cluster_count > 7]
#df = df[df.test_cluster_count > 6]

#best_df = DataFrame()
#for symbol, df_symbol in df.groupby('_symbol'):
#    best_result = analyzer.find_best_filter_combination(df_symbol)
#    best_df = pd.concat([best_df, best_result["filtered_df"]], axis=0, ignore_index=True)


#best_df = best_df[best_df.wilson_score > 0.35]

#best_df = best_df[
#    (best_df["_test_precision"] >= 0.8) &
#    (best_df["wilson_score"] >= 0.55) &
#    (best_df["_test_reward"] >= 7) &
#    (best_df["_test_trade_count"] >= 10) &
#    (best_df["cluster_count"] <= 17) &
#    (best_df["test_cluster_count"] > 7) &
#    (best_df["train_index_median_distance"] >= 5)
#]

analyzer.analyze(best_df)
antwort = input("Möchtest du speichern? (y/N): ").strip().lower()

if antwort == "y":
    best_df.to_parquet(live_parquet_name)
    best_df.to_parquet(train_parquet_name)
    #ycache.save_parquet_model("predictor_filtered.parquet", best_df)
else:
    print("No Save")








