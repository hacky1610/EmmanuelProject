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


class StockChart:
    def __init__(self, df, title):
        """
        Erstellt eine Instanz des StockChart-Plotters.
        :param df: DataFrame mit den Spalten ['timestamp', 'open', 'high', 'low', 'close']
        """
        self.df = df
        self.signals = []
        self.limits = []
        self.stops = []
        self.manual_stops = []
        self.i_stops = []
        self._title = title

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

    def add_manual_stop(self, price):
        """
        Fügt eine Stop-Loss-Linie hinzu.
        :param price: Preis der Stop-Loss-Linie
        """
        self.manual_stops.append(price)

    def add_i_stop(self, price):
        """
        Fügt eine Stop-Loss-Linie hinzu.
        :param price: Preis der Stop-Loss-Linie
        """
        self.i_stops.append(price)

    def plot(self, save_as_html=False, filename="plot.html"):
        """
        Plottet den Aktienkursverlauf mit den Trading-Signalen, Limits und Stops.
        Optional kann der Plot als HTML gespeichert werden.
        """
        fig, ax = plt.subplots(figsize=(14, 8))  # Größeren Plot setzen

        ax.plot(self.df['date'], self.df['close'], label='Close Price', color='blue')

        # Signale einzeichnen
        signal_labels = set()
        for time, price, signal_type in self.signals:
            color = 'green' if signal_type == 'start' else 'red'
            label = f'{signal_type.capitalize()} Signal'
            if label not in signal_labels:
                ax.scatter(time, price, color=color, marker='o', label=label)
                signal_labels.add(label)
            else:
                ax.scatter(time, price, color=color, marker='o')

        # Limit- und Stop-Loss-Linien
        if self.limits:
            ax.hlines(self.limits, xmin=self.df['date'].min(), xmax=self.df['date'].max(),
                      colors='orange', linestyles='--', label='Limit')
        if self.stops:
            ax.hlines(self.stops, xmin=self.df['date'].min(), xmax=self.df['date'].max(),
                      colors='red', linestyles='--', label='Stop-Loss')

        if self.manual_stops:
            ax.hlines(self.manual_stops, xmin=self.df['date'].min(), xmax=self.df['date'].max(),
                      colors='orange', linestyles='--', label='Manual Stop')

        if self.i_stops:
            ax.hlines(self.i_stops, xmin=self.df['date'].min(), xmax=self.df['date'].max(),
                      colors='purple', linestyles='--', label='I Stop')

        ax.set_xlabel('Zeit')
        ax.set_ylabel('Preis')
        ax.set_title(self._title)
        ax.legend()

        if save_as_html:
            html_str = f"""
            <html>
            <head>
                <style>
                    .container {{
                        width: 100%;
                        height: 100vh;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                    }}
                    .plot {{
                        width: 90%;
                        height: 90%;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="plot"></div>
                </div>
            </body>
            </html>
            """

            with open(filename, "w") as f:
                f.write(html_str)
            print(f"Plot als HTML gespeichert: {filename}")
        else:
            plt.show(block=True)

pd.set_option('future.no_silent_downcasting', True)
for deal in reversed(list(ds.get_closed_deals())):
    # if deal['dealId'] != "DIAAAATGT8KLDAZ":
    #      continue
    if deal["open_date_ig_datetime"] > datetime.now() - timedelta(hours=24):
        continue

    id = deal["predictor_scan_id"]
    predictor = ps.load_by_id(id)
    predictor_object = DeepPredictor(deal["ticker"], cache, Indicators(), config=predictor)
    df, df_eval = tiingo.load_test_data(deal["ticker"], DataProcessor(), trade_type=TradeType.FX,
                                                            use_cache=True, days=30)

    chart_index_open = search_index(df, deal["open_date_ig_datetime"])
    chart_index_close = search_index(df, deal["close_date_ig_datetime"])

    chart = StockChart(df, f"{deal['ticker']} - {deal['direction']} {deal['profit']} {deal['dealId']}")
    chart.add_trade_signal(df['date'][chart_index_open], deal["open_level"], 'start')
    chart.add_trade_signal(df['date'][chart_index_close], deal["close_level"], 'end')

    if deal['direction'] == "buy":
        chart.add_limit(df['close'][chart_index_open] + df['ATR'][chart_index_open] * predictor_object.get_atr_factor_limit() )

        chart.add_stop(df['close'][chart_index_open] - df['ATR'][chart_index_open] * predictor_object.get_atr_factor_stop())
        chart.add_manual_stop(
            deal["manual_stop_level"])
        chart.add_i_stop(
            deal["intelligent_stop_level"])

    else:
        chart.add_limit(
            df['close'][chart_index_open] - df['ATR'][chart_index_open] * predictor_object.get_atr_factor_limit())

        chart.add_stop(
            df['close'][chart_index_open] + df['ATR'][chart_index_open] * predictor_object.get_atr_factor_stop())

    chart.plot(save_as_html=False, filename=f"{id}.html")
input("Drücke Enter zum Beenden...")



