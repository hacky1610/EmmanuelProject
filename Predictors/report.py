import dropbox
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
indicators = []
#endregion

currency_markets = ig.get_markets(TradeType.FX, tradeable=False)

r = Reporting()
results, df = r.report_predictors(currency_markets,GenericPredictor,df_cache)

print(results)

def shop_pie(name:str):
    fig = px.pie(df, values=name, names=name, title=name)
    fig.show()

def shop_pie_bool(name:str):
    true_count = df[name].sum()
    false_count = len(df) - true_count

    true_percentage = (true_count / len(df)) * 100
    false_percentage = (false_count / len(df)) * 100

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

df.fillna(0,inplace=True)


fig = px.bar(df, x='symbol', y='frequence')
fig.show()
fig = px.bar(df.sort_values(by=["win_los"]), x='symbol', y='win_los')
fig.show()

# Zählen Sie die Häufigkeit der Elemente
elemente_häufigkeit = Counter(indicators)

# Vorbereiten der Daten für das Balkendiagramm
x_werte = list(elemente_häufigkeit.keys())
y_werte = list(elemente_häufigkeit.values())

sortierte_daten = sorted(zip(x_werte, y_werte), key=lambda x: x[1], reverse=True)
x_werte_sortiert, y_werte_sortiert = zip(*sortierte_daten)

# Erstellen Sie das Balkendiagramm
fig = px.bar(x=x_werte_sortiert, y=y_werte_sortiert, labels={'x': 'Elemente', 'y': 'Häufigkeit'})

# Diagramm anzeigen
fig.show()



