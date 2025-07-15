import os
import string
import time
from datetime import datetime, timedelta
from random import random, choices

import pandas
import pandas as pd
import pymongo

from BL import DataProcessor
from BL.Simulation import Simulation
from BL.analytics import Analytics
from BL.combination_trainer import CombinationTrainer
from BL.datatypes import TradeAction
from BL.indicators import Indicators
from Connectors.IG import IG
from Connectors.deal_store import DealStore
from Connectors.dropbox_cache import DropBoxCache
from Connectors.market_store import MarketStore
from Connectors.predictore_store import PredictorStore
from Connectors.tiingo import Tiingo, TradeType
from BL.utils import ConfigReader
import dropbox
from Connectors.dropboxservice import DropBoxService
from Predictors.chart_pattern_rectangle import RectanglePredictor
from Predictors.deep_predictor import DeepPredictor
from Predictors.generic_predictor import GenericPredictor
from UI.base_viewer import BaseViewer
from UI.plotly_viewer import PlotlyViewer

def generate_random_string(length=10):
    characters = string.ascii_letters + string.digits  # Includes A-Z, a-z, 0-9
    return ''.join(choices(characters, k=length))



conf_reader = ConfigReader()
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx,"DEMO")
cache = DropBoxCache(ds, prefix=generate_random_string(12))
tiingo = Tiingo(conf_reader=conf_reader, cache=cache)
ig = IG(conf_reader=conf_reader)
predictor = GenericPredictor(indicators=Indicators(), symbol="Foo")
viewer = PlotlyViewer(cache)
client = pymongo.MongoClient(f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster1.uo3fjln.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ds = DealStore(db, "DEMO")
ps = PredictorStore(db)
sim = Simulation(cache, Analytics(MarketStore(db), ig))
ct = CombinationTrainer(cache, Indicators(),ps, test_mode=True)
ti = Tiingo(conf_reader=conf_reader, cache=cache)
os.environ["PYTHONWARNINGS"] = "ignore"


while True:
    df, df_eval = tiingo.load_test_data("USDSGD", DataProcessor(), trade_type=TradeType.FX,
                                                            use_cache=False, days=300)

    print(df[-10:][["date","close"]])
    time.sleep(60 * 65)






