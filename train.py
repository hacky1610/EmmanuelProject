# region import
import os
import random
from multiprocessing import Process
from typing import Type

import pymongo

from BL.async_executor import AsyncExecutor
from BL.indicators import Indicators
from Connectors.IG import IG
from Connectors.dropbox_cache import DropBoxCache
from Connectors.market_store import MarketStore
from Connectors.tiingo import TradeType, Tiingo
from Predictors.chart_pattern_rectangle import RectanglePredictor
from Predictors.chart_pattern_triangle import TrianglePredictor
from Predictors.generic_predictor import GenericPredictor
from Predictors.joy_predictor import JoyPredictor
from Predictors.trainer import Trainer
from BL.utils import ConfigReader
from BL.data_processor import DataProcessor
from BL.analytics import Analytics
from Connectors.dropboxservice import DropBoxService
import dropbox

from Predictors.utils import Reporting

# endregions

type_ = "DEMO"
if type_ == "DEMO":
    live = False
else:
    live = True

# region statics
conf_reader = ConfigReader(live_config=live)
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx, type_)
cache = DropBoxCache(ds)
client = pymongo.MongoClient(f"mongodb+srv://emmanuel:qkcGMAdpjKF1I7Jw@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ms = MarketStore(db)
_trainer = Trainer(Analytics(market_store=ms), cache=cache, check_trainable=False)
_tiingo = Tiingo(conf_reader=conf_reader, cache=cache)
_dp = DataProcessor()
_trade_type = TradeType.FX
_ig = IG(conf_reader=conf_reader, live=live)
_async_ex = AsyncExecutor(free_cpus=2)
_indicators = Indicators()
_reporting = Reporting(cache)
# endregion

_train_version = "V2.20"
_loop = True
_async_exec =False # os.name != "nt"


def train_predictor(ig: IG,
                    trainer: Trainer,
                    tiingo: Tiingo,
                    async_ex: AsyncExecutor,
                    dp: DataProcessor,
                    train_version: str,
                    predictor: Type,
                    async_exec: bool,
                    indicators: Indicators,
                    reporting:Reporting,
                    trade_type: TradeType = TradeType.FX,
                    ):
    markets = ig.get_markets(tradeable=False, trade_type=trade_type)
    if len(markets) == 0:
        return
    reporting.create(markets, predictor)
    best_indicators = reporting.get_best_indicator_names()
    #print(f"Best indicators: {best_indicators}")

    for m in random.choices(markets, k=10):
        # for m in markets:
        symbol = m["symbol"]
        #symbol = "EURCZK"
        df_train, eval_df_train = tiingo.load_train_data(symbol, dp, trade_type=trade_type)
        df_test, eval_df_test = tiingo.load_test_data(symbol, dp, trade_type=trade_type)
        if len(df_train) > 0:
            if async_exec:
                if __name__ == '__main__':
                    async_ex.run(trainer.train, args=(symbol, m["scaling"], df_train, eval_df_train,df_test, eval_df_test, train_version, predictor, indicators, best_indicators))
            else:
                try:
                    trainer.train(symbol, m["scaling"], df_train, eval_df_train,df_test, eval_df_test, train_version, predictor, indicators, best_indicators)
                except:
                    print("Error")
        else:
            print(f"No Data in {symbol} ")


while True:

    train_predictor(ig=_ig,
                    trainer=_trainer,
                    tiingo=_tiingo,
                    predictor=GenericPredictor,
                    async_ex=_async_ex,
                    async_exec=_async_exec,
                    train_version=_train_version,
                    dp=_dp,
                    reporting=_reporting,
                    indicators=_indicators)

    # train_predictor(ig=_ig,
    #                 trainer=_trainer,
    #                 tiingo=_tiingo,
    #                 predictor=JoyPredictor,
    #                 async_ex=_async_ex,
    #                 async_exec=_async_exec,
    #                 train_version=_train_version,
    #                 dp=_dp,
    #                 reporting=_reporting,
    #                 indicators=_indicators)

    # train_predictor(ig=_ig,
    #                 trainer=_trainer,
    #                 tiingo=_tiingo,
    #                 predictor=RectanglePredictor,
    #                 async_ex=_async_ex,
    #                 async_exec=_async_exec,
    #                 train_version=_train_version,
    #                 dp=_dp,
    #                 indicators=_indicators)
    # train_predictor(ig=_ig,
    #                 trainer=_trainer,
    #                 tiingo=_tiingo,
    #                 predictor=TrianglePredictor,
    #                 async_ex=_async_ex,
    #                 async_exec=_async_exec,
    #                 train_version=_train_version,
    #                 dp=_dp,
    #                 indicators=_indicators)
