from typing import List

import dropbox
from pandas import DataFrame

from Connectors.dropbox_cache import DropBoxService, DropBoxCache
from Connectors.IG import IG
from BL import  ConfigReader
from Connectors.tiingo import  TradeType
import plotly.express as px
import pandas as pd
from collections import Counter
from Predictors.generic_predictor import GenericPredictor
from Predictors.utils import Reporting

#region members
conf_reader = ConfigReader()
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx,"DEMO")
df_cache = DropBoxCache(ds)
ig = IG(ConfigReader())
#endregion

#region functions
def shop_pie(name:str, reports:DataFrame):
    fig = px.pie(reports, values=name, names=name, title=name)
    fig.show()

def shop_pie_bool(name:str, reports:DataFrame ):
    true_count = reports[name].sum()
    false_count = len(reports) - true_count

    true_percentage = (true_count / len(reports)) * 100
    false_percentage = (false_count / len(reports)) * 100

    percentage_df = pd.DataFrame({
        'Label': ['True', 'False'],
        'Percentage': [true_percentage, false_percentage]
    })

    percentage_df = pd.DataFrame({
        'Label': ['True', 'False'],
        'Percentage': [true_percentage, false_percentage]
    })

    fig = px.pie(percentage_df, names='Label', values='Percentage',
                 title=name)
    fig.show()

def show_indicators(indicators):
    # Vorbereiten der Daten für das Balkendiagramm
    x_werte = list(indicators.keys())
    y_werte = list(indicators.values())
    sortierte_daten = sorted(zip(x_werte, y_werte), key=lambda x: x[1], reverse=True)
    x_werte_sortiert, y_werte_sortiert = zip(*sortierte_daten)
    # Erstellen Sie das Balkendiagramm
    fig = px.bar(x=x_werte_sortiert, y=y_werte_sortiert, labels={'x': 'Elemente', 'y': 'Häufigkeit'})
    # Diagramm anzeigen
    fig.show()

#endregion

_currency_markets = ig.get_markets(TradeType.FX, tradeable=False)

_reporting = Reporting(df_cache)
_reporting.create(_currency_markets, GenericPredictor)


print(_reporting.results)


fig = px.bar(_reporting.reports, x='symbol', y='frequence')
fig.show()
fig = px.bar(_reporting.reports.sort_values(by=["win_los"]), x='symbol', y='win_los')
fig.show()


show_indicators(_reporting.get_all_indicators())
show_indicators(_reporting.get_best_indicators())

reps = _reporting.reports[_reporting.reports.trades < 200]
(px.scatter(y=reps.win_los, x=reps.trades)).show()






