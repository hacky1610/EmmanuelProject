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


import matplotlib.pyplot as plt
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


class StockChart:
    def __init__(self, df):
        """
        Erstellt eine Instanz des StockChart-Plotters.
        :param df: DataFrame mit den Spalten ['timestamp', 'open', 'high', 'low', 'close']
        """
        self.df = df
        self.signals = []
        self.limits = []
        self.stops = []

    def add_trade_signal(self, time, price, signal_type):
        """
        Fügt ein Trade-Signal hinzu.
        :param time: Zeitpunkt des Signals
        :param price: Preis des Signals
        :param signal_type: 'start' oder 'end'
        """
        self.signals.append((time, price, signal_type))

    def add_limit(self, price):
        """
        Fügt eine Limit-Linie hinzu.
        :param price: Preis der Limit-Linie
        """
        self.limits.append(price)

    def add_stop(self, price):
        """
        Fügt eine Stop-Loss-Linie hinzu.
        :param price: Preis der Stop-Loss-Linie
        """
        self.stops.append(price)

    def plot(self):
        """
        Plottet den Aktienkursverlauf mit den Trading-Signalen, Limits und Stops.
        """
        plt.figure(figsize=(12, 6))
        plt.plot(self.df['date'], self.df['close'], label='Close Price', color='blue')

        # Signale einzeichnen
        for time, price, signal_type in self.signals:
            color = 'green' if signal_type == 'start' else 'red'
            plt.scatter(time, price, color=color, marker='o', label=f'{signal_type.capitalize()} Signal')

        # Limit-Linien
        for price in self.limits:
            plt.axhline(y=price, color='orange', linestyle='--', label='Limit')

        # Stop-Loss-Linien
        for price in self.stops:
            plt.axhline(y=price, color='red', linestyle='--', label='Stop-Loss')

        plt.xlabel('Zeit')
        plt.ylabel('Preis')
        plt.legend()
        plt.title('Aktienkursverlauf mit Trading-Signalen')
        plt.show()

pd.set_option('future.no_silent_downcasting', True)
for deal in ds.get_all_deals_opened_after():
    # if deal["dealId"] != "DIAAAAS2KELNCAK":
    #     continue

    id = deal["predictor_scan_id"]
    predictor = ps.load_by_id(id)
    predictor_object = DeepPredictor(deal["ticker"], cache, Indicators(), config=predictor)
    df, df_eval = tiingo.load_test_data(deal["ticker"], DataProcessor(), trade_type=TradeType.FX,
                                                            use_cache=True, days=30)

    chart_index_open = search_index(df, deal["open_date_ig_datetime"])
    chart_index_close = search_index(df, deal["close_date_ig_datetime"])

    chart = StockChart(df)
    chart.add_trade_signal(df['date'][chart_index_open], df['close'][chart_index_open], 'start')
    chart.add_trade_signal(df['date'][chart_index_close], df['close'][chart_index_close], 'end')
    #chart.add_limit(120)
    #chart.add_stop(90)

    chart.plot()
    exit(0)


