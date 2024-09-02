import pymongo
from Connectors.IG import IG
from BL import ConfigReader
from Connectors.predictore_store import PredictorStore
import plotly.express as px
from Predictors.generic_predictor import GenericPredictor
from Predictors.utils import Reporting

#region members
conf_reader = ConfigReader()
client = pymongo.MongoClient(
    f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ps = PredictorStore(db)
#endregion

#region functions

def show_indicators(indicators):
    x_werte = list(indicators.keys())
    y_werte = list(indicators.values())
    sortierte_daten = sorted(zip(x_werte, y_werte), key=lambda x: x[1], reverse=True)
    x_werte_sortiert, y_werte_sortiert = zip(*sortierte_daten)
    fig = px.bar(x=x_werte_sortiert, y=y_werte_sortiert, labels={'x': 'Elemente', 'y': 'Häufigkeit'})
    fig.show()

#endregion

_reporting = Reporting(ps)
_reporting.create(IG.get_markets_offline(), GenericPredictor)

print(_reporting.results)

show_indicators(_reporting.get_all_indicators())
show_indicators(_reporting.get_best_indicators())

reps = _reporting.reports
(px.scatter(y=reps.win_los, x=reps.trades)).show()
