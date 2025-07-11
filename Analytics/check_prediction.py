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
    target_time = date.replace(hour= 0, minute=0, second=0, microsecond=0)
    target_time = target_time - timedelta(days=1)

    # Index des nächstgelegenen Zeitpunkts finden
    nearest_index = (df_new["date"] - target_time).abs().idxmin()

    # Den Chartindex ausgeben
    return nearest_index

pd.set_option('future.no_silent_downcasting', True)
for deal in reversed(list(ds.get_open_deals_raw())):
    if "predictor_object" not in deal:
        continue

    if deal["predictor_object"] is None:
        continue

    if deal["dealId"] != "DIAAAAUBMT9C2BC":
        continue


    predictor_object = DeepPredictor(deal["ticker"], cache, Indicators(), config=deal["predictor_object"])
    print(f'+++{deal["ticker"]}')
    #continue

    df, df_eval = tiingo.load_test_data(deal["ticker"], DataProcessor(), trade_type=TradeType.FX,
                                                            use_cache=False, days=300)
    yesterday = tiingo.get_last_hour_of_yesterday(deal["ticker"], DataProcessor(), trade_type=TradeType.FX)

    if "index" in df.columns:
        df = df.drop(columns="index")

    chart_index = search_index(df, deal["open_date_ig_datetime"])


    buy_results, sell_results = sim.simulate(df, df_eval, deal["ticker"],
                                                    time_frame=16,factor_limit=predictor_object.get_atr_factor_limit(), factor_stop=predictor_object.get_atr_factor_stop(), force=True)
    sim.get_signals_by_indicatornames(deal["ticker"], df, predictor_object._features, Indicators(), GenericPredictor)
    train_signals_df = sim.create_combined_indicator_data_by_features(predictor_object._features, deal["ticker"], "test")
    trade_results = []
    pd.set_option('future.no_silent_downcasting', True)
    # Set specific replacement values for each trade type
    if predictor_object._trade_mode == TradeAction.BUY:
        train_signals_df = train_signals_df.replace({'none': 0, 'both': 1, 'buy': 1, 'sell': 0})
        trade_results = buy_results
    elif predictor_object._trade_mode == TradeAction.SELL:
        train_signals_df = train_signals_df.replace({'none': 0, 'both': 1, 'buy': 0, 'sell': 1})
        trade_results = sell_results

    train_signals_df = train_signals_df.infer_objects(copy=False)



    # Prepare results data
    trade_results = trade_results[['chart_index', 'result', "entry_time"]]
    trade_results['result'] = trade_results['result'].apply(lambda x: 1 if x > 0 else 0)
    signal_result_df = pd.merge(train_signals_df, trade_results, on='chart_index', how='left')
    signal_result_df['result'] = signal_result_df['result'].fillna(0)
    signal_result_df = signal_result_df.dropna()

    if not  signal_result_df[signal_result_df.chart_index == chart_index][predictor_object._features].sum(axis=1).item() == len(predictor_object._features):
        print("ERROR!!!")
    else:
        print("OK")





