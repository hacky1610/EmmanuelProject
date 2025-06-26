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
client = pymongo.MongoClient(f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster1.uo3fjln.mongodb.net/?retryWrites=true&w=majority")
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
won_features = [
]
lost_features = []

for deal in reversed(list(ds.get_closed_deals())):
    # if deal['dealId'] != "DIAAAATFAPCUBA7":
    #      continue
    if deal["open_date_ig_datetime"] < datetime.now() - timedelta(hours=200):
        continue

    id = deal["predictor_scan_id"]
    predictor = ps.load_by_id(id)
    predictor_object = DeepPredictor(deal["ticker"], cache, Indicators(), config=predictor)
    if deal['profit'] > 0:
        won_features = won_features + predictor_object._features
    else:
        lost_features = lost_features + predictor_object._features
from collections import Counter
wc = Counter(won_features)
wl = Counter(lost_features)

all_features = set(wc) | set(wl)
difference = {
    feature: wc[feature] - wl[feature]
    for feature in all_features
}

# Sortiert ausgeben: positive Werte => mehr bei Gewinnen
print("📈 Features mit höherer Häufigkeit bei Gewinn-Trades:")
for feature, diff in sorted(difference.items(), key=lambda x: -x[1]):
    if diff > 0:
        print(f"{feature}: +{diff}")

print("\n📉 Features mit höherer Häufigkeit bei Verlust-Trades:")
for feature, diff in sorted(difference.items(), key=lambda x: x[1]):
    if diff < 0:
        print(f"{feature}: {diff}")



