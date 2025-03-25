import os
import string
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
client = pymongo.MongoClient(f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ds = DealStore(db, "DEMO")
ps = PredictorStore(db)
sim = Simulation(cache, Analytics(MarketStore(db), ig))
ct = CombinationTrainer(cache, Indicators(),ps, test_mode=True)
ti = Tiingo(conf_reader=conf_reader, cache=cache)
os.environ["PYTHONWARNINGS"] = "ignore"

def search_index(df, date):
    # date`-Spalte in datetime konvertieren
    df_new = df.copy()
    df_new["date"] = pd.to_datetime(df_new["date"])
    df_new["date"] = df_new["date"].dt.tz_convert(None)

    # Gegebene Zeit (Minuten und Sekunden entfernen)
    target_time = date.replace(minute=0, second=0, microsecond=0)
    target_time = target_time - timedelta(hours=1)

    # Index des nächstgelegenen Zeitpunkts finden
    nearest_index = (df_new["date"] - target_time).abs().idxmin()

    # Den Chartindex ausgeben
    chart_index = df_new.loc[nearest_index, "index"]
    return chart_index

pd.set_option('future.no_silent_downcasting', True)
results = []

for deal in ds.get_all_deals_opened_after():
    # if deal["dealId"] != "DIAAAAS2KELNCAK":
    #     continue

    if deal["status"] != "Closed":
        continue

    id = deal["predictor_scan_id"]
    predictor = ps.load_by_id(id)
    predictor_object = DeepPredictor(deal["ticker"], cache, Indicators(), config=predictor)


    results.append({
        "dealId": deal["dealId"],
        "direction": deal["direction"],
        "ticker": deal["ticker"],
        "profit": deal["profit"],
        "train_reward": predictor["_train_reward"],
        "train_precision": predictor["_train_precision"],
        "test_reward": predictor["_test_reward"],
        "test_precision": predictor["_test_precision"],
        "feature_len": len(predictor["_features"]),
        "features": predictor["_features"]
    })



print(pandas.DataFrame(results))

