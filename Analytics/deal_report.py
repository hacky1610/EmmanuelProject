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
deals_store = DealStore(db, account_type="LIVE")
pred_scans = PredictorStore(db)
ms = MarketStore(db)
dp = DataProcessor()
closed = deals_store.get_closed_deals()
analytics = Analytics(ms)

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

        if "predictor_scan_id" in deal:

            id = deal["predictor_scan_id"]
            if id != '':
                scan = pred_scans.load_by_id(id)
                start = deal["open_date_ig_datetime"] - timedelta(days=50)
                end = deal["close_date_ig_datetime"] + timedelta(days=10)
                if end > datetime.now():
                    end = None
                df_train = tiingo.load_data_by_date(ticker=deal["ticker"],
                                                    start=TimeUtils.get_date_string(start),
                                                    end=TimeUtils.get_date_string(end),
                                                    data_processor=dp,
                                                    trade_type=TradeType.FX,
                                                    resolution="1hour",
                                                    validate=False)

                df_eval_train = tiingo.load_data_by_date(ticker=deal["ticker"],
                                                         start=TimeUtils.get_date_string(start),
                                                         end=TimeUtils.get_date_string(end),
                                                         data_processor=dp,
                                                         trade_type=TradeType.FX,
                                                         resolution="5min",
                                                         validate=False)
                predictor = GenericPredictor(deal["ticker"], indicators=Indicators())
                predictor.setup(scan)
                scaling = ig.get_market_details(deal["epic"])["snapshot"]["scalingFactor"]

                ev_res = analytics.evaluate(predictor, df=df_train, df_eval=df_eval_train, only_one_position=False,
                                            symbol=deal["ticker"], scaling=scaling)

                trades = ev_res.get_trade_results()

                if len(trades) == 0:
                    print("No trades - len is 0")

                matched = False
                for t in trades:
                    if t.open_time == TimeUtils.get_time_string(deal["open_date_ig_datetime"]):
                        print(f"{deal['ticker']} {deal['dealId']}")
                        if t.profit == 0:
                            raise Exception("Profit is 0")

                        matched = True
                        market = ms.get_market(deal['ticker'])
                        ev_res_profit = t.profit * scaling / market.pip_euro
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
                            if not deal["intelligent_stop_used"]:
                                print(f"Error: Real better")
                                print(f"Open time {deal['open_date_ig_datetime']} ")
                                print(f"Error: Real close time {real_res_close_time} open {deal['open_level']} close {deal['close_level']}")
                                print(f"Error: Eval close time {ev_res_close_time} open {t.opening} close {t.closing}")
                                print(f"Eval Result {ev_res_profit}")
                                print(f"Real Result {real_res_profit}")

                        eval_result += ev_res_profit
                        real_result += real_res_profit

                        if deal["intelligent_stop_used"]:
                            eval_intelli_result += ev_res_profit
                            real_intelli_result += real_res_profit
                        else:
                            diff = prozentualer_unterschied(ev_res_profit, real_res_profit)
                            if abs(diff) > 20:
                                print("Error: Big difference")
                                print(f"Diff: {diff}")
                                print(f"Eval Result {ev_res_profit}")
                                print(f"Real Result {real_res_profit}")


                if not matched:
                    print("No matching trades")
    except Exception as e:
        print(f"Error {e}")

print(f"Eval {eval_result}")
print(f"Real {real_result}")
print(f"Eval Intelli {eval_intelli_result}")
print(f"Real Intelli {real_intelli_result}")
