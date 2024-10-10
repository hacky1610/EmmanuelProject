# region import
import random
import traceback
from datetime import datetime, timezone, timedelta
from typing import Dict, List

import pandas as pd
import pymongo
from pandas import DataFrame

from BL import DataProcessor, ConfigReader, measure_time
from BL.analytics import Analytics, PositionEvalResult
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




def eval_symbol(symbol, df:DataFrame, limit:float, stop:float,use_isl:bool=False) -> PositionEvalResult:
    symbol_profit = 0
    symbol_trading_minutes = 0
    df_5_minute_ohlc = get_test_data(tiingo=ti, symbol=symbol, trade_type=trade_type, dp=dp, dropbox_cache=df_cache)
    filtered_market = [d for d in markets if d["symbol"] == symbol]
    if len(filtered_market) == 0 or df_5_minute_ohlc is None:
        return PositionEvalResult(0, 0, 0, 0, datetime(1970,1,1))
    market = filtered_market[0]
    newest_trade = datetime(1970,1,1)
    for _, i in df.iterrows():

        if i.tradeType == "BUY":
            trade_action = TradeAction.BUY
        else:
            trade_action = TradeAction.SELL
        profit, trading_minutes = analytics.evaluate_position(df_eval=df_5_minute_ohlc, symbol=symbol, action=trade_action,
                                                              open_time=datetime.utcfromtimestamp(
                                                                  i["dateOpen"] / 1000).replace(
                                                                  tzinfo=timezone.utc),
                                                              close_time=datetime.utcfromtimestamp(
                                                                  i["dateClosed"] / 1000).replace(
                                                                  tzinfo=timezone.utc),
                                                              epic=market["epic"], scaling=market["scaling"],
                                                              use_isl=use_isl, limit=limit, stop=stop)

        if profit == 0:
            #print(f"error {symbol} {df_5_minute_ohlc.date} {i}")
            pass

        trade_time = (datetime.utcfromtimestamp(
            i["dateOpen"] / 1000))

        if trade_time > newest_trade:
            newest_trade = trade_time

        symbol_profit += profit
        symbol_trading_minutes += trading_minutes
    return PositionEvalResult(symbol_profit, symbol_trading_minutes,
                              symbol_profit / len(df),
                              symbol_trading_minutes / len(df), newest_trade)

def eval_trader(trader, use_isl=False) -> List[Dict]:
    result_list = []

    try:
        small_hist_df = trader.hist._hist_df[trader.hist._hist_df.dateOpen_datetime_utc > "2023-10-01"]

        for symbol in small_hist_df.currency_clean.unique():
            best_overall_profit = PositionEvalResult(0, 0, 0, 0, datetime(1970,1,1))
            best_result = None
            for limit in [30, 45, 60, 75]:
                for stop in [30, 45, 60, 75]:
                    symbol_df = small_hist_df[small_hist_df.currency_clean == symbol]
                    result = eval_symbol(symbol, symbol_df, limit, stop, use_isl)

                    if result.profit > best_overall_profit.profit:
                        best_overall_profit = result
                        best_result = {"symbol": symbol,
                         "profit": result.profit,
                         "trading_minutes": result.trading_minutes,
                         "avg_profit": result.avg_profit,
                         "avg_minutes": result.avg_minutes,
                         "newest_trade": result.newest_trade,
                         "trades": len(symbol_df),
                         "limit": limit,
                         "stop": stop}

            if best_result is not None:
                result_list.append(best_result)



    except Exception as e:
        print(f"{trader} error {e}")
        traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
        print(f"Error: {e} File:{traceback_str}")

    return result_list

markets = IG.get_markets_offline()

traders = ts.get_all_traders(True)
for trader in traders:
    print(f"Train {trader.name}")
    result_list = eval_trader(trader)
    trader.set_evaluation(result_list)
    ts.save(trader)


