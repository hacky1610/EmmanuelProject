import dropbox

from Connectors import DropBoxService, DropBoxCache
from Connectors.IG import IG
from BL import  ConfigReader
from Connectors.tiingo import  TradeType
import plotly.express as px
from pandas import DataFrame,Series
conf_reader = ConfigReader()
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx,"DEMO")
df_cache = DropBoxCache(ds)

from Predictors.chart_pattern import ChartPatternPredictor

ig = IG(ConfigReader())
df = DataFrame()

currency_markets = ig.get_markets(TradeType.FX)
for market in currency_markets:
    symbol = market["symbol"]
    predictor = ChartPatternPredictor(cache=df_cache)
    predictor.load(symbol)
    df = df.append(Series([symbol,
                           predictor._limit_factor,
                           predictor._look_back,
                           predictor._be4after,
                           predictor._max_dist_factor,
                           predictor._straight_factor,
                           predictor.best_result,
                           predictor.frequence],
                          index=["symbol",
                                 "_limit_factor",
                                 "_look_back",
                                 "_be4after",
                                 "_max_dist_factor",
                                 "_straight_factor",
                                 "best_result",
                                 "frequence"]),ignore_index=True)

def shop_pie(name:str):
    fig = px.pie(df, values=name, names=name, title=name)
    fig.show()

df.fillna(0,inplace=True)
shop_pie("_limit_factor")
shop_pie("_look_back")
shop_pie("_be4after")
shop_pie("_max_dist_factor")
shop_pie("_straight_factor")

fig = px.bar(df, x='symbol', y='frequence')
fig.show()
fig = px.bar(df, x='symbol', y='best_result')
fig.show()



