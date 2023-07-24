# region import
import random
from BL import DataProcessor, Analytics, ConfigReader
from Connectors import Tiingo, TradeType, IG, DropBoxCache, DropBoxService, BaseCache
from Predictors.chart_pattern_rectangle import RectanglePredictor
from Predictors.chart_pattern_triangle import TrianglePredictor
from UI.plotly_viewer import PlotlyViewer
from UI.base_viewer import BaseViewer
import dropbox

# endregion

# region static
conf_reader = ConfigReader()
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx, "DEMO")
df_cache = DropBoxCache(ds)
dp = DataProcessor()
ig = IG(conf_reader)
ti = Tiingo(conf_reader=conf_reader, cache=df_cache)
analytics = Analytics()
trade_type = TradeType.FX
win_loss_overall = 0
market_measures = 0
# endregion

viewer = BaseViewer()
#viewer = PlotlyViewer(cache=df_cache)
only_one_position = True
only_test = True
predictor_class = RectanglePredictor

markets = ig.get_markets(tradeable=False, trade_type=trade_type)
#for m in random.choices(markets,k=30):
for m in markets[:20]:
    symbol = m["symbol"]
    #symbol = "AUDUSD"
    df, df_eval = ti.load_train_data(symbol, dp, trade_type)

    if len(df) > 0:
        predictor = predictor_class(cache=df_cache, viewer=viewer)
        predictor.load(symbol)
        ev_result = analytics.evaluate(predictor=predictor,
                                       df_train=df,
                                       df_eval=df_eval,
                                       viewer=viewer,
                                       symbol=symbol,
                                       only_one_position=only_one_position)

        predictor.best_result = ev_result.get_win_loss()
        predictor.best_reward = ev_result.get_reward()
        predictor.trades = ev_result.get_trades()
        predictor.frequence = ev_result.get_trade_frequency()
        if ev_result.get_trades() > 0:
            win_loss_overall = win_loss_overall + ev_result.get_win_loss()
            market_measures = market_measures + 1
        if not only_test:
            predictor.save(symbol)
        viewer.save(symbol)
        print(f"{symbol} - {ev_result}")

print(f"{win_loss_overall / market_measures} avg profit")
