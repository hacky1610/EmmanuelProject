import pandas
import pymongo

from BL import DataProcessor
from BL.analytics import Analytics
from BL.indicators import Indicators
from Connectors.IG import IG
from Connectors.deal_store import DealStore
from Connectors.dropbox_cache import DropBoxCache
from Connectors.tiingo import Tiingo
from BL.utils import ConfigReader
import dropbox
from Connectors.dropboxservice import DropBoxService
from Predictors.chart_pattern_rectangle import RectanglePredictor
from Predictors.generic_predictor import GenericPredictor
from UI.base_viewer import BaseViewer
from UI.plotly_viewer import PlotlyViewer

conf_reader = ConfigReader()
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx,"DEMO")
cache = DropBoxCache(ds)
tiingo = Tiingo(conf_reader=conf_reader, cache=cache)
ig = IG(conf_reader=conf_reader)
predictor = GenericPredictor(indicators=Indicators())
viewer = PlotlyViewer(cache)
client = pymongo.MongoClient(f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
ds = DealStore(db, "DEMO")

deals = list(ds.get_all_deals())
df_deals = pandas.DataFrame(deals)
df_deals_clean = df_deals.dropna(subset=["predictor_data"])

predictore_results = {}

for _,d in df_deals_clean.iterrows():
    for i in d["predictor_data"]["_indicator_names"]:
        predictore_results[i] = predictore_results.get(i, 0) + d["profit"]



print(predictore_results)

