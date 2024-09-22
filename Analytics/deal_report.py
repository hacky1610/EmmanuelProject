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
            #if deal["dealId"] != "DIAAAAP8TRCCUAZ":
            #    continue

            scan = pred_scans.load_by_id(id)
            start = deal["open_date_ig_datetime"] - timedelta(days=50)
            end = deal["close_date_ig_datetime"] + timedelta(days=10)
            if end > datetime.now():
                end = None
            else:
                end = TimeUtils.get_date_string(end)
            df_train = tiingo.load_data_by_date(ticker=deal["ticker"],
                                                start=TimeUtils.get_date_string(start),
                                                end=end,
                                                data_processor=dp,
                                                trade_type=TradeType.FX,
                                                resolution="1hour",
                                                validate=False)

            df_eval_train = tiingo.load_data_by_date(ticker=deal["ticker"],
                                                     start=TimeUtils.get_date_string(start),
                                                     end=end,
                                                     data_processor=dp,
                                                     trade_type=TradeType.FX,
                                                     resolution="5min",
                                                     validate=False)
            predictor = GenericPredictor(deal["ticker"], indicators=Indicators())
            predictor.setup(scan)
            predictor.setup({"_use_isl":True, "_isl_distance": 6, "_isl_factor":0.7, "_isl_open_end": False})
            scaling = ig.get_market_details(deal["epic"])["snapshot"]["scalingFactor"]

            ev_res = analytics.evaluate(predictor, df=df_train, df_eval=df_eval_train, only_one_position=False,
                                        symbol=deal["ticker"], scaling=scaling, time_filter=deal["open_date_ig_datetime"], epic=deal["epic"])

            trades = ev_res.get_trade_results()

            if len(trades) != 1:
                print("Trade count incorrect")

            print(f"{deal['ticker']} {deal['dealId']}")
            t = trades[0]
            if t.profit == 0:
                raise Exception("Profit is 0")

            matched = True
            market = ms.get_market(deal['ticker'])
            ev_res_profit = t.profit
            real_res_profit = deal['profit']
            ev_res_close_time = t.close_time
            real_res_close_time = deal["close_date_ig_datetime"]
            if (real_res_profit < 0 < ev_res_profit):
                print("Error: Real worse ")
                print(f"Open time {deal['open_date_ig_datetime']} ")
                print(f"Error: Real close time {real_res_close_time} open {deal['open_level']} close {deal['close_level']}")
                print(f"Error: Eval close time {ev_res_close_time} open {t.opening} close {t.closing}")
                print(f"Eval Result {ev_res_profit}")
                print(f"Real Result {real_res_profit}")
            elif (real_res_profit > 0 > ev_res_profit):
                print(f"Error: Real better")
                print(f"Open time {deal['open_date_ig_datetime']} ")
                print(f"Error: Real close time {real_res_close_time} open {deal['open_level']} close {deal['close_level']}")
                print(f"Error: Eval close time {ev_res_close_time} open {t.opening} close {t.closing}")
                print(f"Eval Result {ev_res_profit}")
                print(f"Real Result {real_res_profit}")

            eval_result += ev_res_profit
            real_result += real_res_profit

            if deal["intelligent_stop_used"] != t.intelligent_stop_used:
                print(f"Error: intelligent_stop_used not equal")


            diff = prozentualer_unterschied(ev_res_profit, real_res_profit)
            if abs(diff) > 20:
                print("Error: Big difference")
                print(f"Diff: {diff}")
                print(f"Eval Result {ev_res_profit}")
                print(f"Real Result {real_res_profit}")


    except Exception as e:
        traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
        print(f"MainException: {e} File:{traceback_str}")

print(f"Eval {eval_result}")
print(f"Real {real_result}")
print(f"Eval Intelli {eval_intelli_result}")
print(f"Real Intelli {real_intelli_result}")
