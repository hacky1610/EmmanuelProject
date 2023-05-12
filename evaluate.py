from BL.candle import Candle, MultiCandle
from BL.data_processor import DataProcessor
from BL.pricelevels import ZigZagClusterLevels
from Connectors.tiingo import Tiingo, TradeType
from Predictors.ema_macd import EmaMacd
from Predictors.ema_stoch_candle import EmaStochCandle
from Predictors.macd import MACD
from BL.utils import ConfigReader
from Connectors.IG import IG
from BL import Analytics
from Predictors.psar_bb import PsarBb
from Predictors.psar_macd_stoch import PsarMacdStoch
from Predictors.reversal import Reversal
from Predictors.rsi_bb import RsiBB
from Predictors.rsi_bb2 import RsiBB2
from Predictors.rsi_candle import RsiCandle
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
viewer = PlotlyViewer()


for m in ig.get_markets(tradeable=False, trade_type=trade_type):
    symbol = m["symbol"]
    symbol = "GBPUSD"
    df, df_eval = ti.load_live_data(symbol,dp, trade_type)

    zig_zag_percent = 0.2

    zl = ZigZagClusterLevels(peak_percent_delta=zig_zag_percent, merge_distance=None,
                             merge_percent=0.1, min_bars_between_peaks=20, peaks='Low')

    zl.fit(df)

    viewer.plot_levels(df['close'].values, zl.levels, zig_zag_percent)  # in case you want to display chart

    if len(df) > 0:
        predictor = EmaStochCandle()
        predictor.load(symbol)
        reward, avg_reward, trade_freq, win_loss, avg_minutes = analytics.evaluate(predictor=predictor, df_train=df,df_eval= df_eval, viewer=viewer, symbol=symbol)
        predictor.best_result = win_loss
        predictor.best_reward = reward
        predictor.frequence = trade_freq
        predictor.save(symbol)
        print(f"{symbol} - Reward {reward}, success {avg_reward}, trade_freq {trade_freq}, win_loss {win_loss} avg_minutes {avg_minutes}")


