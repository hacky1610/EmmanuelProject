from Connectors.IG import IG
from BL import Analytics, ConfigReader
from Connectors.tiingo import Tiingo, TradeType
import plotly.express as px
from pandas import DataFrame,Series

from Predictors.sup_res_candle import SupResCandle

ig = IG(ConfigReader())
df = DataFrame()

currency_markets = ig.get_markets(TradeType.FX)
for market in currency_markets:
    symbol = market["symbol"]
    predictor = SupResCandle()
    predictor.load(symbol)
    df = df.append(Series([symbol,
                           predictor.zig_zag_percent,
                           predictor.merge_percent,
                           predictor.min_bars_between_peaks,
                           predictor.look_back_days,
                           predictor.period_1,
                           predictor.period_2,
                           predictor.level_section_size,
                           predictor.best_result,
                           predictor.frequence],
                          index=["symbol",
                                 "zig_zag_percent",
                                 "merge_percent",
                                 "min_bars_between_peaks",
                                 "look_back_days",
                                 "period_1",
                                 "period_2",
                                 "level_section_size",
                                 "best_result",
                                 "frequence"]),ignore_index=True)

def shop_pie(name:str):
    fig = px.pie(df, values=name, names=name, title=name)
    fig.show()

df.fillna(0,inplace=True)
shop_pie("zig_zag_percent")
shop_pie("merge_percent")
shop_pie("min_bars_between_peaks")
shop_pie("look_back_days")
shop_pie("level_section_size")

fig = px.bar(df, x='symbol', y='frequence')
fig.show()
fig = px.bar(df, x='symbol', y='best_result')
fig.show()



