from Connectors.IG import IG
from BL import Analytics, ConfigReader
from Connectors.tiingo import Tiingo, TradeType
from Predictors.rsi_bb import RsiBB
import plotly.express as px
from pandas import DataFrame,Series

ig = IG(ConfigReader())
df = DataFrame()

currency_markets = ig.get_markets(TradeType.FX)
for market in currency_markets:
    symbol = market["symbol"]
    predictor = RsiBB()
    predictor.load(symbol)
    df = df.append(Series([symbol,
                           predictor.rsi_trend,
                           predictor.bb_change,
                           predictor.rsi_upper_limit,
                           predictor.rsi_lower_limit,
                           predictor.period_1,
                           predictor.period_2,
                           predictor.peak_count,
                           predictor.best_result,
                           predictor.frequence],
                          index=["symbol",
                                 "RSI_Trend",
                                 "BB_Change",
                                 "rsi_upper_limit",
                                 "rsi_lower_limit",
                                 "period_1",
                                 "period_2",
                                 "peak_count",
                                 "best_result",
                                 "frequence"]),ignore_index=True)

df.fillna(0,inplace=True)
fig = px.pie(df, values='BB_Change', names='BB_Change', title='BB CHange')
fig.show()
fig = px.pie(df, values='RSI_Trend', names='RSI_Trend', title='RSI Trend')
fig.show()
fig = px.pie(df, values='rsi_upper_limit', names='rsi_upper_limit', title='RSI Upper')
fig.show()
fig = px.pie(df, values='rsi_lower_limit', names='rsi_lower_limit', title='RSI Lower')
fig.show()
fig = px.pie(df, values='period_1', names='period_1', title='period_1')
fig.show()
fig = px.pie(df, values='period_2', names='period_2', title='period_2')
fig.show()
fig = px.pie(df, values='peak_count', names='peak_count', title='peak_count')
fig.show()
fig = px.bar(df, x='symbol', y='frequence')
fig.show()
fig = px.bar(df, x='symbol', y='best_result')
fig.show()



