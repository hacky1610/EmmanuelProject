from BL import DataProcessor, Analytics, ConfigReader
from BL.high_low_scanner import PivotScanner
from Connectors import Tiingo, TradeType, IG, DropBoxCache, DropBoxService, BaseCache
from Predictors.chart_pattern import ChartPatternPredictor
from UI.plotly_viewer import PlotlyViewer
from UI.base_viewer import BaseViewer
import dropbox

# Prep
conf_reader = ConfigReader()
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx,"DEMO")
df_cache = DropBoxCache(ds)
dp = DataProcessor()
ig = IG(conf_reader)
ti = Tiingo(conf_reader=conf_reader,cache=df_cache)
analytics = Analytics()
trade_type = TradeType.FX

viewer = BaseViewer()
viewer = PlotlyViewer(cache=df_cache)
only_one_position = False
only_test = False



for m in ig.get_markets(tradeable=False, trade_type=trade_type):
    symbol = m["symbol"]
    #symbol = "EURUSD"
    df, df_eval = ti.load_train_data(symbol, dp, trade_type)




    if len(df) > 0:
        predictor = ChartPatternPredictor(cache=df_cache,viewer=viewer)
        predictor.load(symbol)
        reward, avg_reward, trade_freq, win_loss, avg_minutes, trades = analytics.evaluate(predictor=predictor,
                                                                                           df_train=df,
                                                                                           df_eval=df_eval,
                                                                                           viewer=viewer,
                                                                                           symbol=symbol,
                                                                                         only_one_position=only_one_position)
        if win_loss > predictor.best_result:
            print("Better")
        elif win_loss == predictor.best_result:
            print("Same")
        else:
            print("Worse")
        predictor.best_result = win_loss
        predictor.best_reward = reward
        predictor.trades = trades
        predictor.frequence = trade_freq
        if not only_test:
            predictor.save(symbol)
        viewer.save(symbol)
        print(f"{symbol} - Reward {reward}, success {avg_reward}, trade_freq {trade_freq}, win_loss {win_loss} avg_minutes {avg_minutes}")


