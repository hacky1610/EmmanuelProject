# region import
import random
import traceback
from datetime import datetime, timezone, timedelta
from typing import Dict

import pandas as pd
import pymongo
from pandas import DataFrame

from BL import DataProcessor, ConfigReader, measure_time
from BL.analytics import Analytics
from BL.datatypes import TradeAction
from BL.eval_result import EvalResultCollection, EvalResult

from Connectors.IG import IG
from Connectors.deal_store import DealStore
from Connectors.dropbox_cache import DropBoxCache
from Connectors.dropboxservice import DropBoxService
from Connectors.market_store import MarketStore
from Connectors.predictore_store import PredictorStore
from Connectors.tiingo import Tiingo, TradeType
from Connectors.trader_store import TraderStore
from Predictors.base_predictor import BasePredictor
from Predictors.chart_pattern_rectangle import RectanglePredictor
from Predictors.chart_pattern_triangle import TrianglePredictor
from Predictors.generic_predictor import GenericPredictor
from Predictors.ichi_predictor import IchimokuPredictor
from UI.plotly_viewer import PlotlyViewer
from UI.base_viewer import BaseViewer
from BL.indicators import Indicators
import dropbox

# endregion

# region static members
conf_reader = ConfigReader()
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx, "DEMO")
df_cache = DropBoxCache(ds)
dp = DataProcessor()
ig = IG(conf_reader)
ti = Tiingo(conf_reader=conf_reader, cache=df_cache)
indicators = Indicators()
client = pymongo.MongoClient(
    f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ms = MarketStore(db)
ds = DealStore(db, "DEMO")
analytics = Analytics(ms, ig)
trade_type = TradeType.FX
ps = PredictorStore(db)
_viewer = BaseViewer()

ts = TraderStore(db)

def get_test_data(tiingo: Tiingo, symbol: str, trade_type: TradeType, dp: DataProcessor,
                  dropbox_cache: DropBoxCache) -> (DataFrame, DataFrame):
    minute_df = f"{symbol}_test_5minute.csv"

    if  dropbox_cache.train_cache_exist(minute_df):
        eval_df_train = dropbox_cache.load_train_cache(minute_df)


    else:
        df_train, eval_df_train = tiingo.load_test_data(symbol, dp, trade_type=trade_type, days=400)
        dropbox_cache.save_train_cache(eval_df_train, minute_df)

    return eval_df_train

def eval_trader(trader):
    try:
        overall_profit_trader = 0
        trader_name = trader.name
        trader_trading_minutes = 0

        small_hist_df = trader.hist._hist_df[trader.hist._hist_df.dateOpen_datetime_utc > "2023-10-01"]

        for symbol in small_hist_df.currency.unique():
            overall_profit_trader_symbol = 0
            for _, i in small_hist_df[small_hist_df.currency == symbol].iterrows():
                s = symbol.replace("/", "")
                market = [d for d in markets if d["symbol"] == s][0]
                df = get_test_data(tiingo=ti, symbol=s, trade_type=trade_type, dp=dp, dropbox_cache=df_cache)
                if i.tradeType == "BUY":
                    trade_action = TradeAction.BUY
                else:
                    trade_action = TradeAction.SELL
                profit, trading_minutes = analytics.evaluate_position(df_eval=df, symbol=s, action=trade_action,
                                                                      open_time=datetime.utcfromtimestamp(
                                                                          i["dateOpen"] / 1000).replace(
                                                                          tzinfo=timezone.utc),
                                                                      close_time=datetime.utcfromtimestamp(
                                                                          i["dateClosed"] / 1000).replace(
                                                                          tzinfo=timezone.utc),
                                                                      epic=market["epic"], scaling=market["scaling"],
                                                                      use_isl=False)

                if profit == 0:
                    print(f"error {trader_name} {symbol}")

                trader_trading_minutes += trading_minutes
                overall_profit_trader_symbol += profit
                overall_profit_trader += profit

            print(f"{trader_name} {symbol} - {overall_profit_trader_symbol:.2f}€")

        print(f"*****{trader_name} - {overall_profit_trader:.0f}€ {(trader_trading_minutes / len(trader.hist._hist_df)):.0f}")
    except Exception as e:
        print(f"{trader} error")

markets = IG.get_markets_offline()

trader = ts.get_trader_by_name("ReVeR273")
eval_trader(trader)

for trader in ts.get_all_traders():
    eval_trader(trader)
