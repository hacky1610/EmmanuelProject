from BL.data_processor import DataProcessor
from Connectors.tiingo import Tiingo, TradeType
from BL.utils import ConfigReader
from Connectors.IG import IG
from BL import Analytics
from Predictors.sup_res_candle import SupResCandle
from UI.plotly_viewer import PlotlyViewer
from UI.base_viewer import BaseViewer
from Connectors.dropbox_cache import DropBoxCache
from Connectors.dropboxservice import DropBoxService
import dropbox

# Prep
conf_reader = ConfigReader()
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx,"DEMO")
cache = DropBoxCache(ds)
dp = DataProcessor()
ig = IG(conf_reader)
ti = Tiingo(conf_reader=conf_reader,cache=cache)
analytics = Analytics()
trade_type = TradeType.FX

viewer = BaseViewer()
viewer = PlotlyViewer()

for m in ig.get_markets(tradeable=False, trade_type=trade_type):
    symbol = m["symbol"]
    symbol = "EURJPY"
    df, df_eval = ti.load_live_data(symbol,dp, trade_type)

    if len(df) > 0:
        predictor = SupResCandle(viewer=viewer)
        predictor.load(symbol)
        reward, avg_reward, trade_freq, win_loss, avg_minutes, trades = analytics.evaluate(predictor=predictor, df_train=df,df_eval= df_eval, viewer=viewer, symbol=symbol)
        predictor.best_result = win_loss
        predictor.best_reward = reward
        predictor.trades = trades
        predictor.frequence = trade_freq
        predictor.save(symbol)
        print(f"{symbol} - Reward {reward}, success {avg_reward}, trade_freq {trade_freq}, win_loss {win_loss} avg_minutes {avg_minutes}")


