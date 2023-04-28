import os

from BL.data_processor import DataProcessor
from Connectors.tiingo import Tiingo, TradeType
from Predictors.rsi_bb import RsiBB
from BL.utils import ConfigReader, get_project_dir
from Connectors.IG import IG
from BL import Analytics
from pandas import DataFrame,Series
from UI.plotly_viewer import PlotlyViewer
from UI.base_viewer import BaseViewer

# Prep
conf_reader = ConfigReader()
dp = DataProcessor()
ig = IG(conf_reader)
ti = Tiingo(conf_reader=conf_reader)
analytics = Analytics()
trade_type = TradeType.FX
viewer = BaseViewer()
#viewer = PlotlyViewer()

evaluate_results = DataFrame()

for m in ig.get_markets(tradeable=False, trade_type=trade_type):
    symbol = m["symbol"]
    symbol = "AUDUSD"
    df, df_eval = ti.load_live_data(symbol,dp, trade_type)

    if len(df) > 0:
        predictor = RsiBB()
        predictor.load(symbol)
        reward, avg_reward, trade_freq, win_loss, avg_minutes = analytics.evaluate(predictor, df, df_eval, viewer)
        evaluate_results = evaluate_results.append(Series([symbol,reward,avg_reward,trade_freq,win_loss,avg_minutes], index=["symbol","reward","avg_reward","trade_freq","win_loss","avg_minutes"]),ignore_index=True)
        print(f"{symbol} - Reward {reward}, success {avg_reward}, trade_freq {trade_freq}, win_loss {win_loss} avg_minutes {avg_minutes}")

evaluate_results.to_json(os.path.join(get_project_dir(),"Settings", "evaluation.json"))

