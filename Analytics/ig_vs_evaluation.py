import traceback
from datetime import timedelta, datetime

import pymongo

from BL.data_processor import DataProcessor
from BL.analytics import Analytics
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
from Predictors.generic_predictor import GenericPredictor
from Predictors.utils import TimeUtils
from UI.plotly_viewer import PlotlyViewer

conf_reader = ConfigReader()
dbx = dropbox.Dropbox(conf_reader.get("dropbox"))
ds = DropBoxService(dbx, "DEMO")
cache = DropBoxCache(ds)
tiingo = Tiingo(conf_reader=conf_reader, cache=cache)
ig = IG(conf_reader=conf_reader)
viewer = PlotlyViewer(cache)

client = pymongo.MongoClient(
    f"mongodb+srv://emmanuel:{conf_reader.get('mongo_db')}@cluster0.3dbopdi.mongodb.net/?retryWrites=true&w=majority")
db = client["ZuluDB"]
account_type = "DEMO"
deals_store = DealStore(db, account_type=account_type)
pred_scans = PredictorStore(db)
ms = MarketStore(db)
dp = DataProcessor()
vor_7_tagen = datetime.now() - timedelta(days=7)
closed = deals_store.get_custom({"status": "Closed",
                                 "account_type": account_type,
                                 'predictor_scan_id': {'$exists': True},
                                 "open_date_ig_datetime": {'$gt': vor_7_tagen}})
analytics = Analytics(ms, ig)

eval_result = 0
real_result = 0
eval_intelli_result = 0
real_intelli_result = 0
intelligent_result_balance = 0

def prozentualer_unterschied(wert1, wert2):
    durchschnitt = (wert1 + wert2) / 2
    differenz = abs(wert1 - wert2)
    prozentualer_unterschied = (differenz / durchschnitt) * 100
    return prozentualer_unterschied

for deal in closed:
    try:
        id = deal["predictor_scan_id"]
        if id != '':
            #if deal["dealId"] != "DIAAAAP5XLHRVAC":
            #    continue

            scan = pred_scans.load_by_id(id)
            p = GenericPredictor(indicators=Indicators(), symbol=deal["ticker"], viewer=viewer)
            p.setup(scan)


            print(f"{deal['profit']} Reward {p.get_result().get_reward()} WL {p.get_result().get_win_loss()} Avg {p.get_result().get_average_reward()}")


    except Exception as e:
        traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
        print(f"MainException: {e} File:{traceback_str}")

print(f"Eval {eval_result}")
print(f"Real {real_result}")
print(f"Eval Intelli {eval_intelli_result}")
print(f"Real Intelli {real_intelli_result}")
