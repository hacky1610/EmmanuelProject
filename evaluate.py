from BL import DataProcessor, Analytics, ConfigReader
from Connectors import Tiingo, TradeType, IG, DropBoxCache, DropBoxService, BaseCache
from Predictors.combo import Combo
from Predictors.sr_break import SRBreak
from Predictors.sr_candle_rsi import SRCandleRsi
from Predictors.sup_res_candle import SupResCandle
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
only_one_position = True



#for m in ig.get_markets(tradeable=False, trade_type=trade_type):
    #symbol = m["symbol"]
symbol = "AUDUSD"
df, df_eval = ti.load_train_data(symbol, dp, trade_type)

if len(df) > 0:
    predictor = SRCandleRsi(cache=df_cache)
    predictor.load(symbol)
    reward, avg_reward, trade_freq, win_loss, avg_minutes, trades = analytics.evaluate(predictor=predictor,
                                                                                       df_train=df,
                                                                                       df_eval=df_eval,
                                                                                       viewer=viewer,
                                                                                       symbol=symbol,
                                                                                       only_one_position=only_one_position)
    predictor.best_result = win_loss
    predictor.best_reward = reward
    predictor.trades = trades
    predictor.frequence = trade_freq
    predictor.save(symbol)
    viewer.save(symbol)
    print(f"{symbol} - Reward {reward}, success {avg_reward}, trade_freq {trade_freq}, win_loss {win_loss} avg_minutes {avg_minutes}")


